import socket
import ssl
import urllib.parse

SOCKET_CACHE = {}
###example urls http://example.org  file:///path/goes/here data:text/html,Hello world!
class URL:
    def __init__(self, url):
        #check for view-source and flag


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

    def request(self, redirect_count = 0):
        if self.scheme == "file":
            f = open(self.path, encoding="utf8")
            return f.read()

        if self.scheme == "data":
            metadata, content = self.path.split(",", 1)
            return urllib.parse.unquote(content)
        
        #use socket cache to reuse open ports
        key = (self.host, self.port)

        if key in SOCKET_CACHE:
            s = SOCKET_CACHE[key]
        else:
            s = socket.socket(
                family = socket.AF_INET,
                type = socket.SOCK_STREAM,
                proto = socket.IPPROTO_TCP,)
            
            s.connect((self.host,self.port))
            if self.scheme == "https":
                ctx = ssl.create_default_context()
                s = ctx.wrap_socket(s, server_hostname=self.host)
            SOCKET_CACHE[key] = s

        #Headers Dictionary,  add any headers to
        headers = {
            "Host": self.host,
            "Connection": "keep-alive",
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
        response = s.makefile("rb")
        statusline = response.readline().decode("utf8")
        version,status,explanation = statusline.split(" ", 2)
        response_headers = {}
        while True:
            line = response.readline().decode("utf8")
            if line =="\r\n": break
            header,value = line.split(":", 1)
            response_headers[header.casefold()] = value.strip()
        #redirect
        if status.startswith("3"):
            if redirect_count > 5:
                raise Exception("Too Many Redirects")
            redirect_url = response_headers.get("location")
            if redirect_url.startswith("/"):
                redirect_url = f"{self.scheme}://{self.host}{redirect_url}"
            new_url = URL(redirect_url)
            return new_url.request(redirect_count + 1)

        
        #print response headers
        # print("Response Headers:")
        # for header, value in response_headers.items():
        #     print(f"{header}: {value}")

        assert "transfer-encoding" not in response_headers
        assert "content-encoding" not in response_headers
        length = int(response_headers["content-length"])
        content = response.read(length).decode("utf8")
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

    # print("\n\n--second request--\n")

    # url2 = URL(sys.argv[1])
    # load(url2)