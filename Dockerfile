FROM python:3.8-slim

ENV VIRTUAL_ENV=/opt/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

#install dependencies
COPY requirements.txt /bot/
WORKDIR /bot/
RUN pip install -r requirements.txt

COPY . /bot/
CMD ["python3","kurzgesagt.py"]
