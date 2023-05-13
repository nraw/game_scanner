prod:
	uvicorn app:app --host=0.0.0.0 --port=5000

deploy:
	gcloud functions deploy game_scanner --allow-unauthenticated --entry-point=main --gen2 --runtime=python311 --max-instances=1 --trigger-http --env-vars-file=.env
