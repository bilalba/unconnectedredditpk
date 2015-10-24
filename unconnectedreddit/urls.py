from django.conf.urls import patterns, include, url
from django.contrib.auth.decorators import login_required as auth
from django.contrib import admin
from links.models import UserProfile, Vote
from django.views.generic.base import TemplateView
from links.views import LinkListView, UserProfileDetailView, UserProfileEditView, LinkCreateView, LinkDetailView, LinkUpdateView, LinkDeleteView, VoteFormView, ScoreHelpView, UserSettingsEditView, HelpView, UnseenActivityView, WhoseOnlineView, RegisterHelpView, VerifyHelpView, PublicreplyView, ReportreplyView, UserActivityView, ReportView, HistoryHelpView #MyRegistrationView


admin.autodiscover()

urlpatterns = patterns('',
	url(r'^admin/', include(admin.site.urls)),
	url(r'^$', LinkListView.as_view(), name='home'),
	url(r'^login/$', 'django.contrib.auth.views.login', {'template_name': 'login.html'}, name="login"),
	url(r'^logout/$', 'django.contrib.auth.views.logout_then_login', name="logout"),
	#url(r'^register/$', MyRegistrationView.as_view(), name='registration_register'),
	#url(r'^register/closed/$', TemplateView.as_view(template_name='registration/registration_closed.html'),
	#                      name='registration_disallowed'),
	#(r'', include('registration.auth_urls')),
	url(r'^users/(?P<slug>[\w.@+-]+)/$', UserProfileDetailView.as_view(), name='profile'),#r'^[\w.@+-]+$'
	url(r'^edit_settings/$', auth(UserSettingsEditView.as_view()), name="edit_settings"),
	url(r'^edit_profile/$', auth(UserProfileEditView.as_view()), name='edit_profile'),
	url(r'^accounts/', include('registration.backends.simple.urls')),
	url(r'^online_kone/$', auth(WhoseOnlineView.as_view()), name='online_kone'),
	url(r'^users/(?P<slug>[\w.@+-]+)/activity/$', auth(UserActivityView.as_view()), name="user_activity"),
	url(r'^users/(?P<slug>[\w.@+-]+)/unseen/$', auth(UnseenActivityView.as_view()), name="unseen_activity"),
	url(r'^link/create/$', LinkCreateView.as_view(), name='link_create'),
	url(r'^link/(?P<pk>\d+)/$', LinkDetailView.as_view(), name='link_detail'),
	url(r'^score/$', auth(ScoreHelpView.as_view()), name='score_help'),
	url(r'^history/$', auth(HistoryHelpView.as_view()), name='history_help'),
	url(r'^help/$', HelpView.as_view(), name='help'),
	url(r'^register_help/$', RegisterHelpView.as_view(), name='register_help'),
	url(r'^verify_help/$', VerifyHelpView.as_view(), name='verify_help'),
	url(r'^link/update/(?P<pk>\d+)/$', auth(LinkUpdateView.as_view()), name='link_update'),
	url(r'^link/delete/(?P<pk>\d+)/$', auth(LinkDeleteView.as_view()), name='link_delete'),
	url(r'^comments/', include('django.contrib.comments.urls')),
	url(r'^vote/$', VoteFormView.as_view(), name="vote"),
	url(r'^link/(?P<pk>\d+)/reply/$', auth(PublicreplyView.as_view()), name="reply"),
	url(r'^report/(?P<pk>\d+)/$', auth(ReportreplyView.as_view()), name="reportreply"),
	url(r'^report/$', auth(ReportView.as_view()), name="report"),

)