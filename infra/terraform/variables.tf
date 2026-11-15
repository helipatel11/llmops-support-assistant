variable "aws_region" {
  default = "us-east-1"
}

variable "instance_type" {
  description = "t3.large (2 vCPU, 8 GB): fits k3s + Ollama (tinyllama, nomic-embed-text) + monitoring."
  default     = "t3.large"
}

variable "key_name" {
  description = "Existing EC2 key pair used for SSH."
  default     = "llmops-key"
}

variable "admin_cidr" {
  description = "The only source allowed to reach SSH and HTTP, e.g. \"203.0.113.7/32\" (your IP). No default on purpose."
  type        = string
}

variable "k3s_version" {
  default = "v1.30.4+k3s1"
}

variable "ollama_version" {
  default = "0.40.16"
}

variable "github_repo" {
  description = "owner/name of the repo whose main-branch CI may push images (GitHub OIDC)."
  default     = "helipatel11/llmops-support-assistant"
}
