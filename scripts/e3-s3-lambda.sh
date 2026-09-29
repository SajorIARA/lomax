#!/bin/bash
set -e
EP=${AWS_ENDPOINT_URL:-http://floci:4566}
bash infra/s3/crear-buckets.sh
cd infra/lambda && zip -r /tmp/thumb.zip thumbnail.py >/dev/null && cd -
aws --endpoint-url $EP lambda create-function --function-name lomax-thumbnail --runtime python3.12 --handler thumbnail.lambda_handler --role arn:aws:iam::000000000000:role/lambda --zip-file fileb:///tmp/thumb.zip || aws --endpoint-url $EP lambda update-function-code --function-name lomax-thumbnail --zip-file fileb:///tmp/thumb.zip
echo '{"producto_id":"1","bucket_original":"lomax-originales","key_original":"originales/1/original","bucket_thumb":"lomax-miniaturas","key_thumb":"thumbs/1.jpg"}' > /tmp/payload.json
aws --endpoint-url $EP lambda invoke --function-name lomax-thumbnail /tmp/out.json --payload file:///tmp/payload.json || true
cat /tmp/out.json; echo
aws --endpoint-url $EP s3 ls s3://lomax-originales --recursive; aws --endpoint-url $EP s3 ls s3://lomax-miniaturas --recursive
python3 -c "from PIL import Image; im=Image.open('/tmp/thumb_check.jpg') if False else None" || true
