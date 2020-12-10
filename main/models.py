from sqlalchemy import String

import main
from main import db
from flask_sqlalchemy import SQLAlchemy

password = "Passphrase".encode()

class Entry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text)
    password = db.Column(db.Text)
    jsondata = db.Column(db.Text)

    def __repr__(self):
        return "<Entry id={} name={!r} password={!r} jsondata={!r}>".format(self.id, self.name,main.views.decrypt(self.password, password).decode(),self.jsondata)


def init():
    db.create_all()