# Amazon RDS certificate bundle

`rds-global-bundle.pem` holds the public root CA certificates Amazon RDS uses in every region (108 certificates). Outside local mode Django connects to PostgreSQL with `sslmode=verify-full`, and the Dockerfile points `POSTGRES_SSLROOTCERT` at this file, so the app verifies it is talking to the real RDS endpoint.

- Source: https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem
- Downloaded: 25 September 2026
- SHA-256: `e5bb2084ccf45087bda1c9bffdea0eb15ee67f0b91646106e466714f9de3c7e3`

These are public certificates, not secrets. The file is committed rather than downloaded at build so every image is identical and a build needs no network. To refresh it, download from the source above, check it with `sha256sum`, and update the hash and date here.
