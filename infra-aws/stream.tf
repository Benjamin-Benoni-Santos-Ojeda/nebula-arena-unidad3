resource "aws_s3_bucket" "stream" {
  bucket        = "nebula-stream-${data.aws_caller_identity.actual.account_id}-${terraform.workspace}"
  force_destroy = true
}

resource "aws_s3_bucket_public_access_block" "stream" {
  bucket                  = aws_s3_bucket.stream.id
  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false
}

resource "aws_s3_bucket_policy" "stream_public_read" {
  bucket     = aws_s3_bucket.stream.id
  depends_on = [aws_s3_bucket_public_access_block.stream]
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid       = "PublicReadStreamSegments"
      Effect    = "Allow"
      Principal = "*"
      Action    = "s3:GetObject"
      Resource  = "${aws_s3_bucket.stream.arn}/live/nebula/*"
    }]
  })
}
