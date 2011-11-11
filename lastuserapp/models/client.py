# -*- coding: utf-8 -*-
from lastuserapp.models import db, User, BaseMixin
from lastuserapp.utils import newid, newsecret

class Client(db.Model, BaseMixin):
    """OAuth client applications"""
    __tablename__ = 'client'
    #: User who owns this client
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship(User, primaryjoin=user_id == User.id,
        backref = db.backref('clients', cascade="all, delete-orphan"))
    #: Human-readable title
    title = db.Column(db.Unicode(250), nullable=False)
    #: Long description
    description = db.Column(db.Text, nullable=False, default='')
    #: Human-readable owner name
    owner = db.Column(db.Unicode(250), nullable=False)
    #: Website
    website = db.Column(db.Unicode(250), nullable=False)
    #: Redirect URI
    redirect_uri = db.Column(db.Unicode(250), nullable=False)
    #: Notification URI
    notification_uri = db.Column(db.Unicode(250), nullable=True)
    #: Resource URI
    resource_uri = db.Column(db.Unicode(250), nullable=True)
    #: Active flag
    active = db.Column(db.Boolean, nullable=False, default=True)
    #: Allow anyone to login to this app?
    allow_any_login = db.Column(db.Boolean, nullable=False, default=True)
    #: OAuth client key/id
    key = db.Column(db.String(22), nullable=False, unique=True, default=newid)
    #: OAuth client secret
    secret = db.Column(db.String(44), nullable=False, default=newsecret)
    #: Trusted flag: trusted clients are authorized to access user data
    #: without user consent, but the user must still login and identify themself.
    #: When a single provider provides multiple services, each can be declared
    #: as a trusted client to provide single sign-in across the services
    trusted = db.Column(db.Boolean, nullable=False, default=False)


class UserFlashMessage(db.Model, BaseMixin):
    """
    Saved messages for a user, to be relayed to trusted clients.
    """
    __tablename__ = 'userflashmessage'
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship(User, primaryjoin=user_id == User.id,
        backref=db.backref("flashmessages", cascade="delete, delete-orphan"))
    seq = db.Column(db.Integer, default=0, nullable=False)
    category = db.Column(db.Unicode(20), nullable=False)
    message = db.Column(db.Unicode(250), nullable=False)


class Resource(db.Model, BaseMixin):
    """
    Resources are provided by client applications. Other client applications
    can request access to user data at resource servers by providing the
    `name` as part of the requested `scope`.
    """
    __tablename__ = 'resource'
    # Resource names are unique across client apps
    name = db.Column(db.Unicode(20), unique=True, nullable=False)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    client = db.relationship(Client, primaryjoin=client_id == Client.id,
        backref = db.backref('resources', cascade="all, delete-orphan"))
    title = db.Column(db.Unicode(250), nullable=False)
    description = db.Column(db.Text, default='', nullable=False)
    siteresource = db.Column(db.Boolean, default=False, nullable=False)
    trusted = db.Column(db.Boolean, default=False, nullable=False)


class ResourceAction(db.Model, BaseMixin):
    """
    Actions that can be performed on resources. There should always be at minimum
    a 'read' action.
    """
    __tablename__ = 'resourceaction'
    name = db.Column(db.Unicode(20), nullable=False)
    resource_id = db.Column(db.Integer, db.ForeignKey('resource.id'), nullable=False)
    resource = db.relationship(Resource, primaryjoin=resource_id == Resource.id,
        backref = db.backref('actions', cascade="all, delete-orphan"))
    title = db.Column(db.Unicode(250), nullable=False)
    description = db.Column(db.Text, default='', nullable=False)

    # Action names are unique per client app
    __table_args__ = ( db.UniqueConstraint("name", "resource_id"), {} )


class AuthCode(db.Model, BaseMixin):
    """Short-lived authorization tokens."""
    __tablename__ = 'authcode'
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship(User, primaryjoin=user_id == User.id)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    client = db.relationship(Client, primaryjoin=client_id == Client.id,
        backref = db.backref("authcodes", cascade="all, delete-orphan"))
    code = db.Column(db.String(44), default=newsecret, nullable=False)
    _scope = db.Column('scope', db.Unicode(250), nullable=False)
    redirect_uri = db.Column(db.Unicode(250), nullable=False)
    used = db.Column(db.Boolean, default=False, nullable=False)

    @property
    def scope(self):
        return self._scope.split(u' ')

    @scope.setter
    def scope(self, value):
        self._scope = u' '.join(value)

    scope = db.synonym('_scope', descriptor=scope)

    def add_scope(self, additional):
        if isinstance(additional, basestring):
            additional = [additional]
        self.scope = list(set(self.scope).union(set(additional)))


class AuthToken(db.Model, BaseMixin):
    """Access tokens for access to data."""
    __tablename__ = 'authtoken'
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True) # Null for client-only
    user = db.relationship(User, primaryjoin=user_id == User.id)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    client = db.relationship(Client, primaryjoin=client_id == Client.id,
        backref=db.backref("authtokens", cascade="all, delete-orphan"))
    token = db.Column(db.String(22), default=newid, nullable=False, unique=True)
    token_type = db.Column(db.String(250), default='bearer', nullable=False) # 'bearer', 'mac' or a URL
    secret = db.Column(db.String(44), nullable=True)
    _algorithm = db.Column('algorithm', db.String(20), nullable=True)
    _scope = db.Column('scope', db.Unicode(250), nullable=False)
    validity = db.Column(db.Integer, nullable=False, default=0) # Validity period in seconds
    refresh_token = db.Column(db.String(22), default=newid, nullable=False)

    # Only one authtoken per user and client. Add to scope as needed
    __table_args__ = ( db.UniqueConstraint("user_id", "client_id"), {} )

    def __init__(self, **kwargs):
        super(AuthToken, self).__init__(**kwargs)
        self.token = newid()
        self.refresh_token = newid()
        self.secret = newsecret()

    @property
    def scope(self):
        return self._scope.split(u' ')

    @scope.setter
    def scope(self, value):
        self._scope = u' '.join(value)

    scope = db.synonym('_scope', descriptor=scope)

    def add_scope(self, additional):
        if isinstance(additional, basestring):
            additional = [additional]
        self.scope = list(set(self.scope).union(set(additional)))

    @property
    def algorithm(self):
        return self._algorithm

    @algorithm.setter
    def algorithm(self, value):
        if value is None:
            self._algorithm = None
            self.secret = None
        elif value in ['hmac-sha-1', 'hmac-sha-256']:
            self._algorithm = value
        else:
            raise ValueError, "Unrecognized algorithm '%s'" % value

    algorithm = db.synonym('_algorithm', descriptor=algorithm)


class Permission(db.Model, BaseMixin):
    __tablename__ = 'permission'
    #: User who created this permission
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship(User, primaryjoin=user_id == User.id,
        backref = db.backref('permissions_created', cascade="all, delete-orphan"))
    #: Name token
    name = db.Column(db.Unicode(80), nullable=False)
    #: Human-friendly title
    title = db.Column(db.Unicode(250), nullable=False)
    #: Description of what this permission is about
    description = db.Column(db.Text, default='', nullable=False)
    #: Is this permission available to all users and client apps?
    allusers = db.Column(db.Boolean, default=False, nullable=False)


# This model's name is in plural because it defines multiple permissions within each instance
class UserClientPermissions(db.Model, BaseMixin):
    __tablename__ = 'userclientpermissions'
    # User who has these permissions
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship(User, primaryjoin=user_id == User.id, backref='permissions')
    # Client app they are assigned on
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    client = db.relationship(Client, primaryjoin=client_id == Client.id,
        backref=db.backref('permissions', cascade="all, delete-orphan"))
    # The permissions as a string of tokens
    permissions = db.Column(db.Unicode(250), default=None, nullable=False)

    # Only one assignment per user and client
    # TODO: Also define context for permission:
    # a. User1 has permissions x, y (without context) in app1
    # b. User1 has permissions a, b, c in context p in app1
    __table_args__ = ( db.UniqueConstraint("user_id", "client_id"), {} )


__all__ = ['Client', 'UserFlashMessage', 'Resource', 'ResourceAction', 'AuthCode', 'AuthToken',
    'Permission', 'UserClientPermissions']
