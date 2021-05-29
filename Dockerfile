FROM python:3.8-slim
ENV VIRTUAL_ENV=opt/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . /bot/
WORKDIR /bot/
ENTRYPOINT ["python3"]
CMD ["kurzgesagt.py"]
