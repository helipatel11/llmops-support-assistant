output "public_ip" {
  value = aws_instance.llmops_server.public_ip
}

output "instance_id" {
  value = aws_instance.llmops_server.id
}