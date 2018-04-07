import os
import tornado.ioloop
import tornado.web
import tornado.log
import tornado.web
import queries
from markdown2 import markdown

from jinja2 import \
    Environment, PackageLoader, select_autoescape
  
ENV = Environment(
    loader=PackageLoader('blog', 'templates'),
    autoescape=select_autoescape(['html', 'xml'])
)

class TemplateHandler(tornado.web.RequestHandler):
    def initialize(self):
        self.session = queries.Session(
            'postgresql://postgres@localhost:5432/tornado_blog')
        
    def render_template (self, tpl, context):
        template = ENV.get_template(tpl)
        self.write(template.render(**context))
    
class MainHandler(TemplateHandler):
    def get (self):
        self.render_template("home.html", {})

class CommentHandler(TemplateHandler):
    def post(self, post_id):
        comment = self.get_body_argument('comment')
        self.session.query('''
            INSERT INTO comment VALUES (
            DEFAULT,
            %(comment)s,
            %(post_id)s,
            current_timestamp)
            ''', {'comment': comment, 'post_id': post_id})
        slug = self.session.query('SELECT slug FROM post WHERE id = %(id)s', {'id': post_id})[0]['slug']
        self.redirect("/post/" + slug)

class PostHandler(TemplateHandler):
    def get(self, slug):
        blog_post_data = self.session.query('''
            SELECT * 
            FROM post 
            INNER JOIN author ON author.id = post.author_id
            WHERE slug = %(slug)s
            ''', {'slug': slug})
        blog_post_data = blog_post_data[0]
        blog_post_data['body'] = markdown(blog_post_data['body'])
        comments = self.session.query('''
            SELECT c.comment, c.comment_post_datetime
            FROM comment c
            INNER JOIN post p on p.id = c.post_id
            WHERE p.slug = %(slug)s
            ''', {'slug': slug})
        self.render_template("post.html", {'post': blog_post_data, 'comments': comments})

class AuthorsHandler(TemplateHandler):
    def get(self):
        authors = self.session.query('SELECT * FROM author')
        self.render_template("authors.html", {'authors': authors})

class AuthorPostsHandler(TemplateHandler):
    def get(self, author_id):
        author = self.session.query('SELECT name FROM author WHERE id = %(id)s', {'id': author_id})[0]
        posts = self.session.query('''
            SELECT id, title, slug, post_date
            FROM post
            WHERE author_id = %(id)s
            ORDER BY post_date
            ''', {'id': author_id})
        self.render_template("author_posts.html", {'posts': posts, 'author': author})
        

def make_app():
    return tornado.web.Application([
        (r"/", MainHandler),
        (r"/post/(.*)/comment", CommentHandler),
        (r"/post/(.*)", PostHandler),
        (r"/authors", AuthorsHandler),
        (r"/author/(.*)", AuthorPostsHandler),
        (r"/static/(.*)", 
            tornado.web.StaticFileHandler, {'path': 'static'}),
        ], autoreload=True)
  
if __name__ == "__main__":
    tornado.log.enable_pretty_logging()
    app = make_app()
    # setting a static port to allow for database access at same time
    app.listen('8888')
    # app.listen(int(os.environ.get('PORT', '8000')))
    tornado.ioloop.IOLoop.current().start()