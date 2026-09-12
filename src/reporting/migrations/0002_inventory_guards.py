from django.db import migrations


FORWARD = """
CREATE FUNCTION foundation_inventory_version_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'Inventory versions are append-only' USING ERRCODE = '23514';
    ELSIF TG_OP = 'INSERT' THEN
        IF NEW.sealed THEN
            RAISE EXCEPTION 'Create inventory unsealed, insert rows, then seal' USING ERRCODE = '23514';
        END IF;
    ELSE
        IF OLD.sealed OR NOT NEW.sealed OR
           (to_jsonb(NEW) - 'sealed') IS DISTINCT FROM (to_jsonb(OLD) - 'sealed') THEN
            RAISE EXCEPTION 'Only the unsealed to sealed transition is allowed' USING ERRCODE = '23514';
        END IF;
        IF NOT EXISTS (SELECT 1 FROM reporting_inventorysnapshot WHERE inventory_id = OLD.id) THEN
            RAISE EXCEPTION 'Cannot seal empty inventory' USING ERRCODE = '23514';
        END IF;
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER inventory_version_guard BEFORE INSERT OR UPDATE OR DELETE
ON reporting_inventoryversion FOR EACH ROW EXECUTE FUNCTION foundation_inventory_version_guard();

CREATE FUNCTION foundation_inventory_row_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
    selected reporting_inventoryversion%ROWTYPE;
    product_namespace text;
BEGIN
    IF TG_OP <> 'INSERT' THEN
        RAISE EXCEPTION 'Inventory rows are append-only' USING ERRCODE = '23514';
    END IF;
    -- Serialize inserts with sealing so a published version cannot gain rows.
    SELECT * INTO selected FROM reporting_inventoryversion WHERE id = NEW.inventory_id FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Unknown inventory version' USING ERRCODE = '23503';
    END IF;
    SELECT namespace INTO product_namespace FROM catalogue_product WHERE id = NEW.product_id;
    IF selected.sealed OR product_namespace IS DISTINCT FROM selected.namespace THEN
        RAISE EXCEPTION 'Sealed or mismatched inventory version' USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER inventory_row_guard BEFORE INSERT OR UPDATE OR DELETE
ON reporting_inventorysnapshot FOR EACH ROW EXECUTE FUNCTION foundation_inventory_row_guard();

CREATE FUNCTION foundation_run_inventory_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE selected reporting_inventoryversion%ROWTYPE;
BEGIN
    IF TG_OP = 'UPDATE' AND (NEW.inventory_id, NEW.cutoff, NEW.window_start)
        IS DISTINCT FROM (OLD.inventory_id, OLD.cutoff, OLD.window_start) THEN
        RAISE EXCEPTION 'Run inventory and reporting window are immutable' USING ERRCODE = '23514';
    END IF;
    SELECT * INTO selected FROM reporting_inventoryversion WHERE id = NEW.inventory_id;
    IF NOT FOUND OR NOT selected.sealed OR selected.cutoff IS DISTINCT FROM NEW.cutoff THEN
        RAISE EXCEPTION 'Run requires a sealed inventory at the same cutoff' USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER run_inventory_guard BEFORE INSERT OR UPDATE
ON reporting_analyticsrun FOR EACH ROW EXECUTE FUNCTION foundation_run_inventory_guard();

CREATE FUNCTION foundation_source_identity_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF (NEW.namespace, NEW.external_id) IS DISTINCT FROM (OLD.namespace, OLD.external_id) THEN
        RAISE EXCEPTION 'Source identity is immutable' USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER product_source_guard BEFORE UPDATE ON catalogue_product
FOR EACH ROW EXECUTE FUNCTION foundation_source_identity_guard();
CREATE TRIGGER customer_source_guard BEFORE UPDATE ON accounts_customerprofile
FOR EACH ROW EXECUTE FUNCTION foundation_source_identity_guard();
CREATE TRIGGER order_source_guard BEFORE UPDATE ON orders_order
FOR EACH ROW EXECUTE FUNCTION foundation_source_identity_guard();

CREATE FUNCTION foundation_order_item_namespace_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF (SELECT namespace FROM orders_order WHERE id = NEW.order_id)
       IS DISTINCT FROM (SELECT namespace FROM catalogue_product WHERE id = NEW.product_id) THEN
        RAISE EXCEPTION 'Order and product namespaces must match' USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER order_item_namespace_guard BEFORE INSERT OR UPDATE ON orders_orderitem
FOR EACH ROW EXECUTE FUNCTION foundation_order_item_namespace_guard();

CREATE FUNCTION foundation_daily_inventory_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM reporting_analyticsrun r JOIN reporting_inventorysnapshot s
        ON s.inventory_id = r.inventory_id WHERE r.id = NEW.run_id AND s.product_id = NEW.product_id
    ) THEN
        RAISE EXCEPTION 'Summary product requires a selected inventory row' USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER daily_inventory_guard BEFORE INSERT OR UPDATE ON reporting_dailyproductsales
FOR EACH ROW EXECUTE FUNCTION foundation_daily_inventory_guard();
"""

REVERSE = """
DROP TRIGGER daily_inventory_guard ON reporting_dailyproductsales;
DROP FUNCTION foundation_daily_inventory_guard();
DROP TRIGGER order_item_namespace_guard ON orders_orderitem;
DROP FUNCTION foundation_order_item_namespace_guard();
DROP TRIGGER order_source_guard ON orders_order;
DROP TRIGGER customer_source_guard ON accounts_customerprofile;
DROP TRIGGER product_source_guard ON catalogue_product;
DROP FUNCTION foundation_source_identity_guard();
DROP TRIGGER run_inventory_guard ON reporting_analyticsrun;
DROP FUNCTION foundation_run_inventory_guard();
DROP TRIGGER inventory_row_guard ON reporting_inventorysnapshot;
DROP FUNCTION foundation_inventory_row_guard();
DROP TRIGGER inventory_version_guard ON reporting_inventoryversion;
DROP FUNCTION foundation_inventory_version_guard();
"""


class Migration(migrations.Migration):
    dependencies = [
        ("reporting", "0001_initial"), ("orders", "0001_initial"),
        ("accounts", "0001_initial"), ("catalogue", "0001_initial"),
    ]
    operations = [migrations.RunSQL(FORWARD, REVERSE)]
