resource "aws_vpc" "nebula" {
  cidr_block           = "10.42.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true
  tags = {
    Name = "nebula-vpc-${terraform.workspace}"
  }
}

resource "aws_internet_gateway" "igw" {
  vpc_id = aws_vpc.nebula.id
  tags = {
    Name = "nebula-igw-${terraform.workspace}"
  }
}

resource "aws_subnet" "publica" {
  count                   = 2
  vpc_id                  = aws_vpc.nebula.id
  cidr_block              = cidrsubnet(aws_vpc.nebula.cidr_block, 8, count.index + 1)
  availability_zone       = data.aws_availability_zones.disponibles.names[count.index]
  map_public_ip_on_launch = true
  tags = {
    Name                                                  = "nebula-public-${count.index + 1}"
    "kubernetes.io/cluster/nebula-${terraform.workspace}" = "shared"
    "kubernetes.io/role/elb"                              = "1"
  }
}

resource "aws_route_table" "publica" {
  vpc_id = aws_vpc.nebula.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.igw.id
  }
  tags = {
    Name = "nebula-rt-public-${terraform.workspace}"
  }
}

resource "aws_route_table_association" "publica" {
  count          = 2
  subnet_id      = aws_subnet.publica[count.index].id
  route_table_id = aws_route_table.publica.id
}

resource "aws_security_group" "gameservers" {
  name        = "nebula-gameservers-sg-${terraform.workspace}"
  description = "Permite trafico TCP/UDP 7000-8000 para partidas Agones y metricas internas"
  vpc_id      = aws_vpc.nebula.id

  ingress {
    description = "Puertos dinamicos de GameServers Agones TCP"
    from_port   = 7000
    to_port     = 8000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "Puertos dinamicos de GameServers Agones UDP"
    from_port   = 7000
    to_port     = 8000
    protocol    = "udp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "Comunicacion interna del cluster"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    self        = true
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
