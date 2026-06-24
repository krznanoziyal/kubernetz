"""
Terraform generator.

Generates:
  terraform/
    main.tf
    variables.tf
    outputs.tf
    backend.tf
    modules/
      vpc/
      eks/
      node-group/
      iam/
      dns/
    environments/
      dev.tfvars
      staging.tfvars
      prod.tfvars
"""
from __future__ import annotations

from .base import BaseGenerator
from ..models.generation import GenerationRequest, GenerationResult
from ..models.platform import CloudProvider, TerraformResourceKind


class TerraformGenerator(BaseGenerator):
    def generate(self, request: GenerationRequest, result: GenerationResult) -> None:
        platform = request.platform
        provider = _primary_provider(platform)

        self._gen_backend(request.terraform_backend, platform.name, result)
        self._gen_main(platform, provider, result)
        self._gen_variables(platform, result)
        self._gen_outputs(result)

        # Modules
        self._gen_vpc_module(provider, result)
        self._gen_k8s_module(provider, result)
        self._gen_node_group_module(provider, result)
        self._gen_iam_module(provider, result)

        # Env var files
        for env in request.environments:
            self._gen_tfvars(env, platform, result)

    # ── Backend ───────────────────────────────────────────────────────────────

    def _gen_backend(self, backend: str, name: str, result: GenerationResult) -> None:
        slug = name.replace("-", "_")
        if backend == "s3":
            content = f"""terraform {{
  backend "s3" {{
    bucket         = "{slug}-terraform-state"
    key            = "terraform.tfstate"
    region         = var.aws_region
    encrypt        = true
    dynamodb_table = "{slug}-terraform-lock"
  }}
}}
"""
        elif backend == "gcs":
            content = f"""terraform {{
  backend "gcs" {{
    bucket = "{slug}-terraform-state"
    prefix = "terraform/state"
  }}
}}
"""
        elif backend == "azurerm":
            content = f"""terraform {{
  backend "azurerm" {{
    resource_group_name  = "{slug}-tfstate"
    storage_account_name = "{slug.replace('_', '')}tfstate"
    container_name       = "tfstate"
    key                  = "terraform.tfstate"
  }}
}}
"""
        else:
            content = """terraform {
  backend "local" {}
}
"""
        result.add_file("terraform/backend.tf", content, "Terraform backend configuration")

    # ── Main ──────────────────────────────────────────────────────────────────

    def _gen_main(self, platform, provider: CloudProvider, result: GenerationResult) -> None:
        pname = platform.name

        if provider == CloudProvider.AWS:
            provider_block = """provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}

provider "kubernetes" {
  host                   = module.eks.cluster_endpoint
  cluster_ca_certificate = base64decode(module.eks.cluster_certificate_authority_data)
  token                  = data.aws_eks_cluster_auth.cluster.token
}

data "aws_eks_cluster_auth" "cluster" {
  name = module.eks.cluster_name
}
"""
            modules = """
module "vpc" {
  source = "./modules/vpc"

  project_name = var.project_name
  environment  = var.environment
  cidr_block   = var.vpc_cidr
  az_count     = var.az_count
}

module "eks" {
  source = "./modules/eks"

  project_name       = var.project_name
  environment        = var.environment
  vpc_id             = module.vpc.vpc_id
  subnet_ids         = module.vpc.private_subnet_ids
  kubernetes_version = var.kubernetes_version
  cluster_name       = "${var.project_name}-${var.environment}"

  depends_on = [module.vpc]
}

module "node_group" {
  source = "./modules/node-group"

  cluster_name    = module.eks.cluster_name
  node_role_arn   = module.iam.node_role_arn
  subnet_ids      = module.vpc.private_subnet_ids
  instance_type   = var.node_instance_type
  min_size        = var.node_min_size
  max_size        = var.node_max_size
  desired_size    = var.node_desired_size

  depends_on = [module.eks]
}

module "iam" {
  source = "./modules/iam"

  project_name = var.project_name
  environment  = var.environment
  cluster_name = module.eks.cluster_name
}
"""
        elif provider == CloudProvider.GCP:
            provider_block = """provider "google" {
  project = var.gcp_project
  region  = var.gcp_region
}
"""
            modules = ""
        else:
            provider_block = """provider "azurerm" {
  features {}
}
"""
            modules = ""

        tf_block = """terraform {
  required_version = ">= 1.6"

  required_providers {
""" + _required_providers(provider) + """
  }
}
"""
        result.add_file("terraform/main.tf", tf_block + "\n" + provider_block + "\n" + modules, "Root Terraform configuration")

    def _gen_variables(self, platform, result: GenerationResult) -> None:
        provider = _primary_provider(platform)
        vars_content = f"""variable "project_name" {{
  description = "Project name, used for resource naming"
  type        = string
  default     = "{platform.name}"
}}

variable "environment" {{
  description = "Deployment environment (dev/staging/prod)"
  type        = string
}}

variable "kubernetes_version" {{
  description = "Kubernetes version for the cluster"
  type        = string
  default     = "1.31"
}}

variable "node_instance_type" {{
  description = "EC2/VM instance type for worker nodes"
  type        = string
  default     = "m5.large"
}}

variable "node_min_size" {{
  description = "Minimum worker nodes"
  type        = number
  default     = 2
}}

variable "node_max_size" {{
  description = "Maximum worker nodes"
  type        = number
  default     = 10
}}

variable "node_desired_size" {{
  description = "Desired worker nodes"
  type        = number
  default     = 3
}}

variable "vpc_cidr" {{
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.0.0.0/16"
}}

variable "az_count" {{
  description = "Number of availability zones"
  type        = number
  default     = 3
}}
"""
        if provider == CloudProvider.AWS:
            vars_content += """
variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}
"""
        elif provider == CloudProvider.GCP:
            vars_content += """
variable "gcp_project" {
  description = "GCP project ID"
  type        = string
}

variable "gcp_region" {
  description = "GCP region"
  type        = string
  default     = "us-central1"
}
"""
        result.add_file("terraform/variables.tf", vars_content, "Terraform input variables")

    def _gen_outputs(self, result: GenerationResult) -> None:
        outputs = """output "cluster_endpoint" {
  description = "Kubernetes API endpoint"
  value       = module.eks.cluster_endpoint
  sensitive   = false
}

output "cluster_name" {
  description = "EKS cluster name"
  value       = module.eks.cluster_name
}

output "vpc_id" {
  description = "VPC ID"
  value       = module.vpc.vpc_id
}

output "kubeconfig_command" {
  description = "Command to update kubeconfig"
  value       = "aws eks update-kubeconfig --region ${var.aws_region} --name ${module.eks.cluster_name}"
}
"""
        result.add_file("terraform/outputs.tf", outputs, "Terraform outputs")

    # ── Modules ───────────────────────────────────────────────────────────────

    def _gen_vpc_module(self, provider: CloudProvider, result: GenerationResult) -> None:
        main = """variable "project_name" { type = string }
variable "environment"  { type = string }
variable "cidr_block"   { type = string default = "10.0.0.0/16" }
variable "az_count"     { type = number default = 3 }

data "aws_availability_zones" "available" { state = "available" }

resource "aws_vpc" "main" {
  cidr_block           = var.cidr_block
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name = "${var.project_name}-${var.environment}-vpc"
  }
}

resource "aws_subnet" "private" {
  count             = var.az_count
  vpc_id            = aws_vpc.main.id
  cidr_block        = cidrsubnet(var.cidr_block, 4, count.index)
  availability_zone = data.aws_availability_zones.available.names[count.index]

  tags = {
    Name                              = "${var.project_name}-${var.environment}-private-${count.index + 1}"
    "kubernetes.io/role/internal-elb" = "1"
  }
}

resource "aws_subnet" "public" {
  count                   = var.az_count
  vpc_id                  = aws_vpc.main.id
  cidr_block              = cidrsubnet(var.cidr_block, 4, count.index + var.az_count)
  availability_zone       = data.aws_availability_zones.available.names[count.index]
  map_public_ip_on_launch = true

  tags = {
    Name                     = "${var.project_name}-${var.environment}-public-${count.index + 1}"
    "kubernetes.io/role/elb" = "1"
  }
}

resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id
  tags   = { Name = "${var.project_name}-${var.environment}-igw" }
}

resource "aws_nat_gateway" "main" {
  count         = var.az_count
  allocation_id = aws_eip.nat[count.index].id
  subnet_id     = aws_subnet.public[count.index].id
  tags          = { Name = "${var.project_name}-${var.environment}-nat-${count.index + 1}" }
  depends_on    = [aws_internet_gateway.main]
}

resource "aws_eip" "nat" {
  count  = var.az_count
  domain = "vpc"
}

output "vpc_id"             { value = aws_vpc.main.id }
output "private_subnet_ids" { value = aws_subnet.private[*].id }
output "public_subnet_ids"  { value = aws_subnet.public[*].id }
"""
        result.add_file("terraform/modules/vpc/main.tf", main, "VPC Terraform module")

    def _gen_k8s_module(self, provider: CloudProvider, result: GenerationResult) -> None:
        main = """variable "cluster_name"       { type = string }
variable "project_name"       { type = string }
variable "environment"        { type = string }
variable "vpc_id"             { type = string }
variable "subnet_ids"         { type = list(string) }
variable "kubernetes_version" { type = string default = "1.31" }

resource "aws_eks_cluster" "main" {
  name     = var.cluster_name
  role_arn = aws_iam_role.cluster.arn
  version  = var.kubernetes_version

  vpc_config {
    subnet_ids              = var.subnet_ids
    endpoint_private_access = true
    endpoint_public_access  = true
    public_access_cidrs     = ["0.0.0.0/0"]
  }

  enabled_cluster_log_types = ["api", "audit", "authenticator", "controllerManager", "scheduler"]

  tags = {
    Name        = var.cluster_name
    Environment = var.environment
  }

  depends_on = [aws_iam_role_policy_attachment.cluster_policy]
}

resource "aws_iam_role" "cluster" {
  name = "${var.cluster_name}-cluster-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "eks.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "cluster_policy" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSClusterPolicy"
  role       = aws_iam_role.cluster.name
}

output "cluster_name"                       { value = aws_eks_cluster.main.name }
output "cluster_endpoint"                   { value = aws_eks_cluster.main.endpoint }
output "cluster_certificate_authority_data" { value = aws_eks_cluster.main.certificate_authority[0].data }
"""
        result.add_file("terraform/modules/eks/main.tf", main, "EKS Terraform module")

    def _gen_node_group_module(self, provider: CloudProvider, result: GenerationResult) -> None:
        main = """variable "cluster_name"  { type = string }
variable "node_role_arn" { type = string }
variable "subnet_ids"    { type = list(string) }
variable "instance_type" { type = string default = "m5.large" }
variable "min_size"      { type = number default = 2 }
variable "max_size"      { type = number default = 10 }
variable "desired_size"  { type = number default = 3 }

resource "aws_eks_node_group" "main" {
  cluster_name    = var.cluster_name
  node_group_name = "${var.cluster_name}-ng"
  node_role_arn   = var.node_role_arn
  subnet_ids      = var.subnet_ids
  instance_types  = [var.instance_type]

  scaling_config {
    desired_size = var.desired_size
    min_size     = var.min_size
    max_size     = var.max_size
  }

  update_config {
    max_unavailable = 1
  }

  labels = {
    role = "worker"
  }

  lifecycle {
    ignore_changes = [scaling_config[0].desired_size]
  }
}
"""
        result.add_file("terraform/modules/node-group/main.tf", main, "Node group Terraform module")

    def _gen_iam_module(self, provider: CloudProvider, result: GenerationResult) -> None:
        main = """variable "project_name" { type = string }
variable "environment"  { type = string }
variable "cluster_name" { type = string }

resource "aws_iam_role" "node" {
  name = "${var.cluster_name}-node-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
    }]
  })
}

locals {
  node_policies = [
    "arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy",
    "arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy",
    "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly",
    "arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy",
  ]
}

resource "aws_iam_role_policy_attachment" "node" {
  for_each   = toset(local.node_policies)
  policy_arn = each.value
  role       = aws_iam_role.node.name
}

output "node_role_arn" { value = aws_iam_role.node.arn }
output "node_role_name" { value = aws_iam_role.node.name }
"""
        result.add_file("terraform/modules/iam/main.tf", main, "IAM Terraform module")

    def _gen_tfvars(self, env: str, platform, result: GenerationResult) -> None:
        node_cfg = {
            "dev": (1, 3, 2, "m5.large"),
            "staging": (2, 5, 3, "m5.large"),
            "prod": (3, 20, 5, "m5.2xlarge"),
        }.get(env, (2, 5, 3, "m5.large"))

        vpc_octet = {"dev": 0, "staging": 1, "prod": 2}.get(env, 0)
        content = f"""# Environment: {env}
project_name    = "{platform.name}"
environment     = "{env}"
aws_region      = "us-east-1"
kubernetes_version = "1.31"
vpc_cidr        = "10.{vpc_octet}.0.0/16"
az_count        = 3
node_instance_type = "{node_cfg[3]}"
node_min_size      = {node_cfg[0]}
node_max_size      = {node_cfg[1]}
node_desired_size  = {node_cfg[2]}
"""
        result.add_file(f"terraform/environments/{env}.tfvars", content, f"Terraform vars for {env}")


def _primary_provider(platform) -> CloudProvider:
    if platform.clusters:
        return platform.clusters[0].provider
    for r in platform.terraform_resources:
        return r.provider
    return CloudProvider.AWS


def _required_providers(provider: CloudProvider) -> str:
    if provider == CloudProvider.AWS:
        return """    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.0"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.0"
    }"""
    if provider == CloudProvider.GCP:
        return """    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }"""
    if provider == CloudProvider.AZURE:
        return """    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }"""
    return ""
