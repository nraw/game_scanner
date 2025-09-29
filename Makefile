test:
	flask --app test_mapper.py run

telegram:
	python3 telegram_app.py

deploy:
	vercel --prod

run:
	vercel dev
