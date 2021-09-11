FROM python:3.9
ADD ./ /zlt-status/

RUN export  DEBIAN_FRONTEND=noninteractive && \
    apt-get update && \
    apt-get -y install libsnmp-dev

WORKDIR /zlt-status 
RUN pip install -r requirements.txt

CMD [ "python", "zlt.py" ]