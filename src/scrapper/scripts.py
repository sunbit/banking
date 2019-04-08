def xhr_intercept_response(match_url, output, request_intercept_script=''):
    return """
        const intercept = (urlmatch, callback) => {{
          let send = XMLHttpRequest.prototype.send;
          XMLHttpRequest.prototype.send = function() {{

            {request_intercept_script}

            this.addEventListener('readystatechange', function() {{
              if (this.responseURL.includes(urlmatch) && this.readyState === 4) {{
                callback(this);
              }}
            }}, false);
            send.apply(this, arguments);
          }};
        }};

        let output = response => {{
            var intercepted = document.getElementById('{output}')
            if (intercepted === null) {{
                intercepted = document.createElement('div');
                intercepted.id = '{output}';
                intercepted.responses = []
                document.body.appendChild(intercepted);
            }}
            if (response.status === 204) {{
                intercepted.responses.push(null)
            }} else {{
                intercepted.responses.push(JSON.parse(response.responseText))
            }}
        }};

        intercept('{match_url}', output);
    """.format(**locals())
