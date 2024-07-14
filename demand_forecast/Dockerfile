FROM public.ecr.aws/lambda/python:3.11

COPY requirements.txt requirements.txt

RUN pip install -r requirements.txt 

COPY scaler.sav .
COPY forecasting.py .
COPY utility_functions.py .
COPY model.ckpt ./model.ckpt

CMD [ "forecasting.lambda_handler" ]