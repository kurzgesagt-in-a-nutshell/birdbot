FROM python:3.8-slim
COPY . /bot/
WORKDIR /bot/
RUN pip install -r requirements.txt
ENTRYPOINT ["python3"]
CMD ["kurzgesagt.py"]
