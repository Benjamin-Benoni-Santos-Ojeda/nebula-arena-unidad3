output "cluster" {
  value = aws_eks_cluster.nebula.name
}

output "registro_ecr" {
  value = aws_ecr_repository.nebula_server.repository_url
}

output "url_clasificacion" {
  value = aws_lambda_function_url.leaderboard.function_url
}

output "bucket_stream" {
  value = aws_s3_bucket.stream.bucket
}

output "url_stream_base" {
  value = "https://${aws_s3_bucket.stream.bucket}.s3.${var.region}.amazonaws.com"
}
