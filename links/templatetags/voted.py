from django.template.defaulttags import register
from links.redismodules import voted_for_link

@register.filter(name='voted')
def voted(link_pk,username):
	return voted_for_link(link_pk, username)