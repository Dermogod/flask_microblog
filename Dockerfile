FROM python:3.6-alpine

RUN adduser -D lev

WORKDIR /home/lev

COPY docker_requirements.txt docker_requirements.txt
RUN python -m venv myvenv
RUN myvenv/bin/pip install -r docker_requirements.txt
RUN myvenv/bin/pip install gunicorn pymysql

COPY app app
COPY migrations migrations
COPY microblog.py config.py boot.sh ./
RUN chmod +x boot.sh

ENV FLASK_APP microblog.py
ENV SECRET_KEY 'you-will-never-guess'
ENV MAIL_SERVER localhost
ENV MAIL_PORT 25
ENV MS_TRANSLATOR_KEY d6dd3ebe7363425bafbde12382214ae9

RUN chown -R lev:lev ./
USER lev

EXPOSE 5001
ENTRYPOINT ["./boot.sh"]