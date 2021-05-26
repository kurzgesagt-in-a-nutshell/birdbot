FROM python:3.8-slim
COPY . /bot/
WORKDIR /bot/
RUN pip install -r requirements.txt
ENTRYPOINT ["python"]
CMD ["kurzgesagt.py"]
