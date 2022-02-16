FROM python:3.7.5
RUN apt update -y && apt upgrade -y
RUN apt-get install -y libglib2.0-0 \
    libnss3 libgconf-2-4 libfontconfig1 \
    sudo \
    openconnect

# install chrome
RUN wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
RUN dpkg -i google-chrome-stable_current_amd64.deb; apt-get -fy install

RUN apt-get clean && \
    rm -rf /var/cache/apt/* && \
    rm -rf /var/lib/apt/lists/*

COPY . ./openconnect-sso
RUN pip install ./openconnect-sso
ENTRYPOINT ["openconnect-sso"]
