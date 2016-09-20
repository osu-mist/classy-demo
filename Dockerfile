FROM python:2.7

RUN pip install gunicorn

ADD requirements.txt /src/requirements.txt
RUN pip install -r /src/requirements.txt

ADD setup.py /src/setup.py
ADD classy /src/classy
RUN pip install -e /src

ENV TZ America/Los_Angeles
ENV CLASSY_CONFIG /src/config.py
USER nobody:nogroup
CMD ["gunicorn", "--bind", ":8000", "classy.app:app"]
