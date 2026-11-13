output "public_ip" {
  value = aws_instance.llmops_server.public_ip
}

output "instance_id" {
  value = aws_instance.llmops_server.id
}

output "ecr_repository_url" {
  value = aws_ecr_repository.app.repository_url
}
