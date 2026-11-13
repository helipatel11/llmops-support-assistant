##################################
# ECR: container images (was created by hand outside Terraform and lost)
##################################

resource "aws_ecr_repository" "app" {
  name                 = "llmops-support-assistant"
  image_tag_mutability = "IMMUTABLE" # a pushed git-SHA tag can never be overwritten
  force_delete         = true        # terraform destroy also removes images (portfolio stack)

  image_scanning_configuration {
    scan_on_push = true # free basic vulnerability scan
  }
}

resource "aws_ecr_lifecycle_policy" "app" {
  repository = aws_ecr_repository.app.name
  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Keep only the 10 most recent images (storage cost)"
      selection = {
        tagStatus   = "any"
        countType   = "imageCountMoreThan"
        countNumber = 10
      }
      action = { type = "expire" }
    }]
  })
}
