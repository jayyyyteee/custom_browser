import socket
import ssl
import urllib.parse

###example urls http://example.org  file:///path/goes/here data:text/html,Hello world!
class URL:
    def __init__(self, url):
        self.view_source = False
        if url.startswith("view-source:"):
            self.view_source = True
            url=url[len("view-source:"):]

        if url.split(":", 1)[0] == "data":
            self.scheme,url = url.split(":",1)
        else:
            self.scheme,url = url.split("://",1)
        

        assert self.scheme in ["http", "https","file","data"]
        if "/" not in url:
            url = url + "/"
        if self.scheme == "file":
            self.path = url
        elif self.scheme == "data":
            self.path = url
        else:
            self.host,url = url.split("/", 1)
            self.path = "/" + url
            if self.scheme == "http":
                self.port = 80
            elif self.scheme == "https":
                self.port = 443
            if ":" in self.host:
                self.host, port = self.host.split(":", 1)
                self.port = int(port)

    def request(self):
        if self.scheme == "file":
            f = open(self.path, encoding="utf8")
            return f.read()

        if self.scheme == "data":
            metadata, content = self.path.split(",", 1)
            return urllib.parse.unquote(content)

        s = socket.socket(
            family = socket.AF_INET,
            type = socket.SOCK_STREAM,
            proto = socket.IPPROTO_TCP,)
        
        s.connect((self.host,self.port))
        if self.scheme == "https":
            ctx = ssl.create_default_context()
            s = ctx.wrap_socket(s, server_hostname=self.host)

        #Headers Dictionary,  add any headers to
        headers = {
            "Host": self.host,
            "Connection": "close",
            "User-Agent": "custom_browser/1.0"
        }
        request = "GET {} HTTP/1.1\r\n".format(self.path)
        for x,y in headers.items():
            request += f"{x}: {y}\r\n"
        request += "\r\n" 
        ###forloop contents
        # request = "GET {} HTTP/1.1\r\n".format(self.path)
        # request += "Host: {}\r\n".format(self.host)
        # request += "Connection: close\r\n"
        # request += "User-Agent: custom_browser/1.0"


        #send contents using utf8 encoding
        s.send(request.encode("utf8"))
        response = s.makefile("r", encoding="utf8", newline="\r\n")
        statusline = response.readline()
        version,status,explanation = statusline.split(" ", 2)
        response_headers = {}
        while True:
            line = response.readline()
            if line =="\r\n": break
            header,value = line.split(":", 1)
            response_headers[header.casefold()] = value.strip()
        assert "transfer-encoding" not in response_headers
        assert "content-encoding" not in response_headers
        content = response.read()
        s.close()
        return content
    
def show(body):
    in_tag = False
    in_entity = False
    entity_buffer = ""
    for c in body: 
        if c == "<":
            in_tag = True
        elif c == ">":
            in_tag = False
        elif in_entity:
            entity_buffer += c
            if c == ";":
                if entity_buffer == "&lt;":
                    print("<", end="")
                elif entity_buffer == "&gt;":
                    print(">", end = "")
                else:
                    print(entity_buffer, end = "")
                in_entity = False
                entity_buffer = ""
        elif c == "&":
            in_entity = True
            entity_buffer = "&"
        elif not in_tag:
            print(c , end="")

def load(url):
    body = url.request()
    if url.view_source:
        print(body, end = "")
    else:
        show(body)

if __name__ == "__main__":
    import sys
    load(URL(sys.argv[1]))
