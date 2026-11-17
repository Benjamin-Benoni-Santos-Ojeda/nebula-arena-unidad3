resource "aws_ecr_repository" "nebula_server" {
  name                 = "nebula-server"
  image_tag_mutability = "MUTABLE"
  force_delete         = true
}

resource "aws_iam_role" "eks_cluster" {
  name = "nebula-eks-cluster-role-${terraform.workspace}"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "eks.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "eks_cluster_policy" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSClusterPolicy"
  role       = aws_iam_role.eks_cluster.name
}

resource "aws_eks_cluster" "nebula" {
  name     = "nebula-${terraform.workspace}"
  role_arn = aws_iam_role.eks_cluster.arn
  version  = "1.30"

  vpc_config {
    subnet_ids              = aws_subnet.publica[*].id
    security_group_ids      = [aws_security_group.gameservers.id]
    endpoint_public_access  = true
    endpoint_private_access = true
  }

  depends_on = [aws_iam_role_policy_attachment.eks_cluster_policy]
}

resource "aws_iam_role" "eks_nodes" {
  name = "nebula-eks-nodes-role-${terraform.workspace}"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "nodes_worker" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy"
  role       = aws_iam_role.eks_nodes.name
}

resource "aws_iam_role_policy_attachment" "nodes_cni" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy"
  role       = aws_iam_role.eks_nodes.name
}

resource "aws_iam_role_policy_attachment" "nodes_ecr" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
  role       = aws_iam_role.eks_nodes.name
}

# Regla en el Security Group principal del clúster EKS para permitir puertos Agones 7000-8000 a los nodos
resource "aws_security_group_rule" "eks_agones_tcp" {
  type              = "ingress"
  from_port         = 7000
  to_port           = 8000
  protocol          = "tcp"
  cidr_blocks       = ["0.0.0.0/0"]
  security_group_id = aws_eks_cluster.nebula.vpc_config[0].cluster_security_group_id
}

resource "aws_security_group_rule" "eks_agones_udp" {
  type              = "ingress"
  from_port         = 7000
  to_port           = 8000
  protocol          = "udp"
  cidr_blocks       = ["0.0.0.0/0"]
  security_group_id = aws_eks_cluster.nebula.vpc_config[0].cluster_security_group_id
}

resource "aws_eks_node_group" "juego" {
  cluster_name    = aws_eks_cluster.nebula.name
  node_group_name = "nebula-nodes"
  node_role_arn   = aws_iam_role.eks_nodes.arn
  subnet_ids      = aws_subnet.publica[*].id
  ami_type        = "AL2023_x86_64_STANDARD"
  instance_types  = [var.tipo_instancia_juego]

  scaling_config {
    desired_size = var.nodos_juego
    min_size     = var.min_nodos_juego
    max_size     = var.max_nodos_juego
  }

  labels = {
    rol = "juego"
  }

  depends_on = [
    aws_iam_role_policy_attachment.nodes_worker,
    aws_iam_role_policy_attachment.nodes_cni,
    aws_iam_role_policy_attachment.nodes_ecr,
  ]
}
