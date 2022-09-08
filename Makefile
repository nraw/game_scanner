prod:
	uvicorn app:app --host=0.0.0.0 --port=5000

docker:
	aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin 172609632730.dkr.ecr.us-west-2.amazonaws.com
	docker build -t wishlist_scanner .
	docker tag wishlist_scanner:latest 172609632730.dkr.ecr.us-west-2.amazonaws.com/wishlist_scanner:latest
	docker push 172609632730.dkr.ecr.us-west-2.amazonaws.com/wishlist_scanner:latest
