FROM python:3.7.3-stretch

RUN apt-get update
RUN apt-get install -y libglib2.0-0=2.50.3-2 \
    libnss3=2:3.26.2-1.1+deb9u1 \
    libgconf-2-4=3.2.6-4+b1 \
    libfontconfig1=2.11.0-6.7+b1 \
    gosu

# Install Chrome for Selenium
RUN curl https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb -o /chrome.deb
RUN dpkg -i /chrome.deb || apt-get install -yf
RUN rm /chrome.deb

RUN mkdir /app
WORKDIR /app

# Install chromedriver for Selenium
# Downloads the lastest release for the currently installed chrome version
RUN curl -s https://chromedriver.storage.googleapis.com/$( curl -s https://chromedriver.storage.googleapis.com/LATEST_RELEASE_$(/opt/google/chrome/chrome --version | sed -r 's/[^0-9]+([0-9\.]+)\..*?/\1/'))/chromedriver_linux64.zip | gunzip > chromedriver
RUN chmod +x /app/chromedriver

COPY Pipfile /app/Pipfile
COPY Pipfile.lock /app/Pipfile.lock

RUN pip install pipenv
RUN pipenv install --python /usr/local/bin/python --deploy --system

COPY src /app/src
EXPOSE 5000
