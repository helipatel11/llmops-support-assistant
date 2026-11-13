##################################
# VPC
##################################

resource "aws_vpc" "llmops_vpc" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name = "llmops-vpc"
  }
}

##################################
# Public Subnet
##################################

resource "aws_subnet" "public_subnet" {
  vpc_id                  = aws_vpc.llmops_vpc.id
  cidr_block              = "10.0.1.0/24"
  map_public_ip_on_launch = true
  availability_zone       = "us-east-1a"

  tags = {
    Name = "llmops-public-subnet"
  }
}

##################################
# Internet Gateway
##################################

resource "aws_internet_gateway" "igw" {
  vpc_id = aws_vpc.llmops_vpc.id

  tags = {
    Name = "llmops-igw"
  }
}

##################################
# Route Table
##################################

resource "aws_route_table" "public_rt" {
  vpc_id = aws_vpc.llmops_vpc.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.igw.id
  }
}

resource "aws_route_table_association" "public_assoc" {
  subnet_id      = aws_subnet.public_subnet.id
  route_table_id = aws_route_table.public_rt.id
}

##################################
# Security Group: only the admin IP can reach SSH and HTTP (Traefik ingress).
# Grafana is served at /grafana through the ingress; Prometheus is port-forward only.
##################################

resource "aws_security_group" "llmops_sg" {
  name   = "llmops-security-group"
  vpc_id = aws_vpc.llmops_vpc.id

  ingress {
    description = "SSH from admin IP"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.admin_cidr]
  }

  ingress {
    description = "HTTP (Traefik ingress) from admin IP"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = [var.admin_cidr]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

##################################
# Latest Ubuntu 22.04 AMI
##################################

data "aws_ami" "ubuntu" {
  most_recent = true

  owners = ["099720109477"]

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }
}

##################################
# EC2: k3s + Ollama, configured at first boot by bootstrap.sh.tftpl
##################################

resource "aws_instance" "llmops_server" {
  ami                  = data.aws_ami.ubuntu.id
  instance_type        = var.instance_type
  key_name             = var.key_name
  iam_instance_profile = aws_iam_instance_profile.node.name

  subnet_id                   = aws_subnet.public_subnet.id
  vpc_security_group_ids      = [aws_security_group.llmops_sg.id]
  associate_public_ip_address = true

  root_block_device {
    volume_size = 40
    volume_type = "gp3"
  }

  # IMDSv2 only, and hop limit 1: containers cannot reach the instance metadata
  # endpoint, so a compromised pod cannot read the node's AWS credentials.
  metadata_options {
    http_tokens                 = "required"
    http_put_response_hop_limit = 1
  }

  user_data = templatefile("${path.module}/bootstrap.sh.tftpl", {
    k3s_version    = var.k3s_version
    ollama_version = var.ollama_version
    region         = var.aws_region
    ecr_registry   = split("/", aws_ecr_repository.app.repository_url)[0]
  })

  tags = {
    Name = "llmops-server"
  }
}
