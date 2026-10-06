output "instance_id" {
  description = "The generator. Open a shell: aws ssm start-session --target <this value>"
  value       = aws_instance.loadgen.id
}
