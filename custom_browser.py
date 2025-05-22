import socket
import ssl
import urllib.parse
import time
import gzip
import tkinter

WIDTH, HEIGHT = 800, 600
SCROLL_STEP = 100
HSTEP, VSTEP = 13, 18
SOCKET_CACHE = {}
RESPONSE_CACHE = {}
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

        #file url
        if self.scheme == "file":
            f = open(self.path, encoding="utf8")
            return f.read()
        
        #data url
        if self.scheme == "data":
            metadata, content = self.path.split(",", 1)
            return urllib.parse.unquote(content)
        
        #use socket cache to reuse open ports
        key = (self.host, self.port)
        response_key = f"{self.scheme}://{self.host}:{self.port}{self.path}"
        
        #response cache
        if response_key in RESPONSE_CACHE:
            print("found in response_cache")
            entry = RESPONSE_CACHE[response_key]
            age = time.time() - entry["timestamp"]
            if age < entry["max_age"]:
                return entry["content"]
            
        #socket cache
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
            "User-Agent": "custom_browser/1.0",
            "Accept-Encoding": "gzip"
            
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

        #gzip/chunked compression
        content_encoding = response_headers.get("content-encoding","").lower()
        transfer_encoding = response_headers.get("transfer-encoding", "").lower()
        if "chunked" in transfer_encoding:
            body = b""
            while True:
                line = response.readline()
                if not line:
                    break
                length = int(line.strip(), 16)
                if length == 0:
                    break
                body += response.read(length)
                response.read(2)
        
        else:
            length = int(response_headers.get("content-length","0"))
            body = response.read(length)

        if "gzip" in content_encoding:
            content = gzip.decompress(body).decode("utf8")

        else:        
            content = body.decode("utf8")

        #cache control parsing
        cache_control = response_headers.get("cache-control", "").lower()
        max_age = 0
        cache = False
        if "no-store" in cache_control:
            cache = False
        else:
            cache = True
            if "max-age=" in cache_control:
                try:
                    max_age = int(cache_control.split("max-age=")[1].split(",")[0])
                    cache = True
                except ValueError:
                    cache = False
            else:
                cache = True
        #save contents to response cache
        if cache and status.startswith("2"):
            RESPONSE_CACHE[response_key] = {
                "timestamp" : time.time(),
                "max_age" : max_age,
                "content" : content
            }
        return content

    
def lex(body):
    in_tag = False
    in_entity = False
    entity_buffer = ""
    text = ""
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
            text += c
    return text


def layout(text):
    display_list = []
    cursor_x, cursor_y = HSTEP, VSTEP
    for c in text:
        if c == "\n":
            cursor_x = HSTEP
            cursor_y += VSTEP * 2 #break for newline
            continue
        display_list.append((cursor_x, cursor_y,  c))
        cursor_x += HSTEP
        if cursor_x >= WIDTH - HSTEP:
            cursor_y += VSTEP
            cursor_x = HSTEP
    return display_list

class Browser:
    def __init__(self):
        self.window = tkinter.Tk()
        self.canvas = tkinter.Canvas(
            self.window,
            width = WIDTH,
            height = HEIGHT
        )
        self.canvas.pack()
        self.scroll = 0
        self.window.bind("<Down>", self.scrolldown)
    
    def scrolldown(self, e):
        self.scroll += SCROLL_STEP
        self.draw()
    
    def draw(self):
        self.canvas.delete("all")
        for x, y, c in self.display_list:
            if y > self.scroll + HEIGHT:continue
            if y + VSTEP < self.scroll: continue
            self.canvas.create_text(x, y-self.scroll, text = c)

    def load(self, url):
        body = url.request()
        if url.view_source:
            self.display_list = layout(body)
            self.draw()
            return 
        text = lex(body)
        self.display_list= layout(text)
        self.draw()


if __name__ == "__main__":
    import sys
    Browser().load(URL(sys.argv[1]))
    tkinter.mainloop()

    # print("\n\n--second request--\n")

    # url2 = URL(sys.argv[1])
    # load(url2)