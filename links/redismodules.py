import redis
import time

POOL = redis.ConnectionPool(host='127.0.0.1', port=6379, db=0)

GRP_TGR = 700

ONE_WEEK = 7*24*60*60
FOUR_DAYS = 4*24*60*60
ONE_DAY = 24*60*60
TWELVE_HOURS = 12*60*60
SIX_HOURS = 6*60*60
THREE_HOURS = 3*60*60
ONE_HOUR = 60*60
TEN_MINS = 10*60
THREE_MINS = 3*60

#####################maintaining group membership#####################

#for each user, keep a list of groups they have been invited to, and list of groups they are a member of
#after 1 week of pushing this update, change group_page to solely a list of groups a person was invited to, or was a member of!

def remove_user_group(user_id, group_id):
	my_server = redis.Redis(connection_pool=POOL)
	set_name = "ug:"+str(user_id) #ug is user's groups
	my_server.srem("ug:"+str(user_id), group_id)

def get_user_groups(user_id):
	my_server = redis.Redis(connection_pool=POOL)
	set_name = "ug:"+str(user_id) #ug is user's groups
	return my_server.smembers(set_name)

def add_user_group(user_id, group_id):
	my_server = redis.Redis(connection_pool=POOL)
	set_name = "ug:"+str(user_id) #ug is user's groups
	my_server.sadd(set_name, group_id)

def get_active_invites(user_id):
	my_server = redis.Redis(connection_pool=POOL)
	unsorted_set = "pir:"+str(user_id) #pir is 'private invite reply' - stores every 'active' invite_id - deleted if reply seen or X is pressed
	return my_server.smembers(unsorted_set)

def remove_group_invite(user_id, group_id):
	my_server = redis.Redis(connection_pool=POOL)
	hash_name = "giu:"+str(group_id)+str(user_id)#giu is 'group invite for user' - stores the invite_id that was sent to the user (for later retrieval)
	invite_id = my_server.hget(hash_name, 'ivt') # get the invite_id to be removed
	my_server.srem("pir:"+str(user_id), invite_id)
	my_server.delete(hash_name)

def check_group_invite(user_id, group_id):
	my_server = redis.Redis(connection_pool=POOL)
	sorted_set = "ipg:"+str(user_id) #ipg is 'invited private group' - this stores the group_id a user has already been invited to - limited to 500 invites
	already_exists = my_server.zscore(sorted_set, group_id)
	if not already_exists:
		return False
	else:
		return True

def add_group_invite(user_id, group_id, invite_id):
	my_server = redis.Redis(connection_pool=POOL)
	sorted_set = "ipg:"+str(user_id) #ipg is 'invited private group' - this stores the group_id a user has already been invited to - limited to 500 invites
	already_exists = my_server.zscore(sorted_set, group_id)
	if not already_exists:
		unsorted_set = "pir:"+str(user_id) #pir is 'private invite reply' - stores every 'active' invite_id - deleted if reply seen or X is pressed
		hash_name = "giu:"+str(group_id)+str(user_id)#giu is 'group invite for user' - stores the invite_id that was sent to the user (for later retrieval)
		size = my_server.zcard(sorted_set)
		limit = 100
		if size > limit: #don't let it overflow - limit its size
			element = my_server.zrange(sorted_set, 0, 0) # get the group_id to be removed
			old_invite_id = my_server.hget("giu:"+element[0]+str(user_id), 'ivt') # get the invite_id to be removed
			my_server.srem("pir:"+str(user_id), old_invite_id) #remove the invite_id
			my_server.delete("giu:"+element[0]+str(user_id)) #remove the related hash
			my_server.zremrangebyrank(sorted_set, 0, 0) #remove the element in question from the sorted set
		my_server.zadd(sorted_set, group_id, time.time()) #where time.time() is the score, and group_id is the value
		my_server.sadd(unsorted_set, invite_id)
		mapping = {'grp':group_id, 'usr':user_id, 'ivt':invite_id}
		my_server.hmset(hash_name, mapping)

def check_group_member(group_id, username):
	my_server = redis.Redis(connection_pool=POOL)
	set_name = "pgm:"+str(group_id) #pgm is private_group_members
	if my_server.sismember(set_name, username):
		return True
	else:
		return False

def remove_group_member(group_id, username):
	my_server = redis.Redis(connection_pool=POOL)
	set_name = "pgm:"+str(group_id) #pgm is private_group_members
	if my_server.exists(set_name):
		if my_server.sismember(set_name, username):
			my_server.srem(set_name, username)
		else:
			pass
	else:
		pass

def add_group_member(group_id, username):
	my_server = redis.Redis(connection_pool=POOL)
	set_name = "pgm:"+str(group_id) #pgm is private_group_members
	if my_server.sismember(set_name, username):
		pass
	else:
		my_server.sadd(set_name, username)

def get_group_members(group_id):
	my_server = redis.Redis(connection_pool=POOL)
	set_name = "pgm:"+str(group_id) #pgm is private_group_members
	if my_server.exists(set_name):
		members = my_server.smembers(set_name)
	else:
		members = None
	return members

#####################checking abuse and punishing#####################

def remove_key(name):
	my_server = redis.Redis(connection_pool=POOL)
	try:
		my_server.delete(name)
	except:
		pass

def private_group_posting_allowed(user_id):
	my_server = redis.Redis(connection_pool=POOL)
	hash_name1 = "pcbah:"+str(user_id)
	hash_name2 = "poah:"+str(user_id)
	time_now = time.time()
	hash_exists1 = my_server.exists(hash_name1)
	hash_exists2 = my_server.exists(hash_name2)
	if hash_exists1 and hash_exists2:
		integrity1 = my_server.hget(hash_name1, "tgr")
		integrity2 = my_server.hget(hash_name2, "tgr")  
		if int(integrity1) < 1 and int(integrity2) < 1:
			last_report_time = my_server.hget(hash_name1, "t")
			if (time_now-float(last_report_time)) < ONE_HOUR: #just banning for one hour for now
				time_remaining = (float(last_report_time)+ONE_HOUR)-time_now
				banned = True
				ban_type = 3
				warned = False
			else:
				my_server.hset(hash_name1, "tgr", GRP_TGR) #refill integrity
				time_remaining = None
				banned = False
				ban_type = None
				warned = False
		elif int(integrity1) < 1:
			last_report_time = my_server.hget(hash_name1, "t")
			if (time_now-float(last_report_time)) < ONE_HOUR: #just banning for one hour for now
				time_remaining = (float(last_report_time)+ONE_HOUR)-time_now
				banned = True
				ban_type = 1
				warned = False
			else:
				my_server.hset(hash_name1, "tgr", GRP_TGR) #refill integrity
				time_remaining = None
				banned = False
				ban_type = None
				warned = False
		elif int(integrity2) < 1:
			last_report_time = my_server.hget(hash_name2, "t")
			if (time_now-float(last_report_time)) < ONE_HOUR: #just banning for one hour for now
				time_remaining = (float(last_report_time)+ONE_HOUR)-time_now
				banned = True
				ban_type = 2
				warned = False
			else:
				my_server.hset(hash_name2, "tgr", GRP_TGR) #refill integrity
				time_remaining = None
				banned = False
				ban_type = None
				warned = False
		elif int(integrity1) < 100 and int(integrity2) < 100: #both integrities are at dangerously low levels
			last_report_time1 = my_server.hget(hash_name1, "t")
			last_report_time2 = my_server.hget(hash_name2, "t")
			least_time = min(float(last_report_time1),float(last_report_time2))
			if (time_now - least_time) < ONE_DAY:
				time_remaining = None
				banned = False
				ban_type = None
				warned = True
			else:
				my_server.hincrby(hash_name1, "tgr", amount=150) #refill 150 integrity
				my_server.hincrby(hash_name2, "tgr", amount=150) #refill 150 integrity
				time_remaining = None
				banned = False
				ban_type = None
				warned = False
		elif int(integrity1) < 100:
			last_report_time = my_server.hget(hash_name1, "t")
			if (time_now - float(last_report_time)) < ONE_DAY:
				time_remaining = None
				banned = False
				ban_type = None
				warned = True
			else:
				my_server.hincrby(hash_name1, "tgr", amount=150) #refill 150 integrity
				time_remaining = None
				banned = False
				ban_type = None
				warned = False
		elif int(integrity2) < 100:
			last_report_time = my_server.hget(hash_name1, "t")
			if (time_now - float(last_report_time)) < ONE_DAY:
				time_remaining = None
				banned = False
				ban_type = None
				warned = True
			else:
				my_server.hincrby(hash_name2, "tgr", amount=150) #refill 150 integrity
				time_remaining = None
				banned = False
				ban_type = None
				warned = False
		else: #no need to warn or ban
			#print "no need to warn or ban"
			time_remaining = None
			banned = False
			ban_type = None
			warned = False
	elif hash_exists1:
		integrity = my_server.hget(hash_name1, "tgr")
		if int(integrity) < 1:
			last_report_time = my_server.hget(hash_name1, "t")
			if (time_now-float(last_report_time)) < ONE_HOUR: #just banning for one hour for now
				time_remaining = (float(last_report_time)+ONE_HOUR)-time_now
				banned = True
				ban_type = 1
				warned = False
			else:
				my_server.hset(hash_name1, "tgr", GRP_TGR) #refill integrity
				time_remaining = None
				banned = False
				ban_type = None
				warned = False
		elif int(integrity) < 100:
			if (time_now-float(last_report_time)) < ONE_DAY:
				time_remaining = None
				banned = False
				ban_type = None
				warned = True
			else:
				my_server.hincrby(hash_name1, "tgr", amount=150) #refilling 150 integrity
				time_remaining = None
				banned = False
				ban_type = None
				warned = False
		else: #no need to warn or ban
			time_remaining = None
			banned = False
			ban_type = None
			warned = False
	elif hash_exists2:
		integrity = my_server.hget(hash_name2, "tgr")
		last_report_time = my_server.hget(hash_name2, "t")
		if int(integrity) < 1:
			if (time_now-float(last_report_time)) < ONE_HOUR: #just banning for one hour for now
				time_remaining = (float(last_report_time)+ONE_HOUR)-time_now
				banned = True
				ban_type = 2
				warned = False
			else:
				my_server.hset(hash_name2, "tgr", GRP_TGR) #refill integrity
				time_remaining = None
				banned = False
				ban_type = None
				warned = False
		elif int(integrity) < 100:
			if (time_now-float(last_report_time)) < ONE_DAY:
				time_remaining = None
				banned = False
				ban_type = None
				warned = True
			else:
				my_server.hincrby(hash_name2, "tgr", amount=150) #refilling 150 integrity
				time_remaining = None
				banned = False
				ban_type = None
				warned = False
		else: #no need to warn or ban
			time_remaining = None
			banned = False
			ban_type = None
			warned = False
	else: #no need to warn or ban
		time_remaining = None
		banned = False
		ban_type = None
		warned = False
	return banned, ban_type, time_remaining, warned

def document_report_reason(user_id, user_score, reporter_id, reporter_cost, desc):
	my_server = redis.Redis(connection_pool=POOL)
	hash_name = "hafs:"+str(user_id)+str(reporter_id) #hafs is 'hash abuse feedback set', it contains strings about the person's wrong doings
	hash_exists = my_server.exists(hash_name)
	if hash_exists:
		return False#already given feedback
	else:
		mapping = {'tgt':user_id, 'scr':user_score, 'rep':reporter_id, 'paid':reporter_cost, 'txt':desc}
		my_server.hmset(hash_name, mapping)
		my_server.sadd("report_reasons", hash_name)
		return True

def document_group_obscenity_abuse(user_id, cost):
	my_server = redis.Redis(connection_pool=POOL)
	hash_name = "poah:"+str(user_id) #poah is 'profile obscenity abuse hash', it contains latest integrity value
	hash_exists = my_server.exists(hash_name)
	if hash_exists:
		hash_time = my_server.hget(hash_name, 't')
		current_time = time.time()
		time_difference = current_time - float(hash_time)
		if time_difference < THREE_HOURS and cost > 80: #if being reported again within three hours and cost paid > 80 (i.e. score 345), increment the punishment_level
			my_server.hincrby(hash_name, "pun", amount=1) #elevating punishment level
			my_server.hset(hash_name, "t", current_time) #updating the time
			integrity_value = my_server.hget(hash_name, 'tgr')
			integrity_value = int(integrity_value) - cost
			if integrity_value < 0:
				integrity_value = 0
			my_server.hset(hash_name, "tgr", integrity_value) #updating the integrity value
		elif time_difference > ONE_WEEK: #if being reported after 7 days, reset punishment and integrity both
			integrity_value = GRP_TGR - cost
			if integrity_value < 0:
				integrity_value = 0
			mapping = {'t': current_time, 'tgr':integrity_value, 'pun':1}
			my_server.hmset(hash_name, mapping)
		elif time_difference > FOUR_DAYS: #if being reported after 4 days, reset the punishment_level
			integrity_value = my_server.hget(hash_name, 'tgr')
			integrity_value = int(integrity_value) - cost
			if integrity_value < 0:
				integrity_value = 0
			mapping = {'t': current_time, 'tgr':integrity_value, 'pun':1}
			my_server.hmset(hash_name, mapping)
		else: #if reported later than three hours but less than 4 days, or less than three hours but low cost, keep punishment_level steady
			my_server.hset(hash_name, "t", current_time)
			integrity_value = my_server.hget(hash_name, 'tgr')
			integrity_value = int(integrity_value) - cost
			if integrity_value < 0:
				integrity_value = 0
			my_server.hset(hash_name, "tgr", integrity_value)
	else:
		value = GRP_TGR #700: around 24 people @ 120 score (30 cost) will cause this person to be banned for 1 hr
		punishment_level = 1
		mapping = {'t': time.time(), 'tgr':value, 'pun':punishment_level}
		my_server.hmset(hash_name, mapping)

def document_group_cyberbullying_abuse(user_id, cost):
	my_server = redis.Redis(connection_pool=POOL)
	hash_name = "pcbah:"+str(user_id) #pcbah is 'profile cyber bullying abuse hash', it contains latest integrity value
	hash_exists = my_server.exists(hash_name)
	if hash_exists:
		hash_time = my_server.hget(hash_name, 't')
		current_time = time.time()
		time_difference = current_time - float(hash_time)
		if time_difference < THREE_HOURS and cost > 80: #if being reported again within three hours and cost paid > 80 (i.e. score 345), increment the punishment_level
			my_server.hincrby(hash_name, "pun", amount=1)
			my_server.hset(hash_name, "t", current_time)
			integrity_value = my_server.hget(hash_name, 'tgr')
			integrity_value = int(integrity_value) - cost
			if integrity_value < 0:
				integrity_value = 0
			my_server.hset(hash_name, "tgr", integrity_value)
		elif time_difference > ONE_WEEK: #if being reported after 7 days, reset punishment and integrity both
			integrity_value = GRP_TGR - cost
			if integrity_value < 0:
				integrity_value = 0
			mapping = {'t': current_time, 'tgr':integrity_value, 'pun':1}
			my_server.hmset(hash_name, mapping)
		elif time_difference > FOUR_DAYS: #if being reported after 4 days, reset the punishment_level
			integrity_value = my_server.hget(hash_name, 'tgr')
			integrity_value = int(integrity_value) - cost
			if integrity_value < 0:
				integrity_value = 0
			mapping = {'t': current_time, 'tgr':integrity_value, 'pun':1}
			my_server.hmset(hash_name, mapping)
		else: #if reported later than three hours but less than 4 days, or less than three hours but low cost, keep punishment_level steady
			my_server.hset(hash_name, "t", current_time)
			integrity_value = my_server.hget(hash_name, 'tgr')
			integrity_value = int(integrity_value) - cost
			if integrity_value < 0:
				integrity_value = 0
			my_server.hset(hash_name, "tgr", integrity_value)
	else:
		value = GRP_TGR #700: around 24 people @ 120 score (30 cost) will cause this person to be banned for 1 hr
		punishment_level = 1
		mapping = {'t': time.time(), 'tgr':value, 'pun':punishment_level}
		my_server.hmset(hash_name, mapping)

def comment_allowed(user_id):
	my_server = redis.Redis(connection_pool=POOL)
	hash_name = "cah:"+str(user_id)
	hash_exists = my_server.exists(hash_name)
	if hash_exists:
		hash_contents = my_server.hgetall(hash_name)
		last_hide_time = hash_contents["t"]
		integrity = int(hash_contents["tgr"])
		time_now = time.time()
		if integrity < -1:
			if (time_now-float(last_hide_time)) < ONE_DAY:
				time_remaining = (float(last_hide_time)+ONE_DAY)-time_now
				banned = True
				warned = False
			else:
				#return their integrity since they've served their time
				my_server.hset(hash_name, "tgr", 5)
				banned = False
				time_remaining = 0
				warned = False
		elif integrity < 0:
			if (time_now-float(last_hide_time)) < TWELVE_HOURS:
				time_remaining = (float(last_hide_time)+TWELVE_HOURS)-time_now
				banned = True
				warned = False
			else:
				#return their integrity since they've served their time
				my_server.hset(hash_name, "tgr", 5)
				banned = False
				time_remaining = 0
				warned = False
		elif integrity < 1:
			if (time_now-float(last_hide_time)) < SIX_HOURS:
				time_remaining = (float(last_hide_time)+SIX_HOURS)-time_now
				banned = True
				warned = False
			else:
				#return their integrity since they've served their time
				my_server.hset(hash_name, "tgr", 5)
				banned = False
				time_remaining = 0
				warned = False
		elif integrity < 2:
			#if last_vote_time was 1 hour ago, let the person post, else he's banned
			if (time_now-float(last_hide_time)) < ONE_HOUR:
				time_remaining = (float(last_hide_time)+ONE_HOUR)-time_now
				banned = True
				warned = False
			else:
				#return their integrity since they've served their time
				my_server.hset(hash_name, "tgr", 5)
				banned = False
				time_remaining = 0
				warned = False
		elif integrity < 3:
			#if last_vote_time was 10 mins ago, let the person post, else he's banned
			if (time_now-float(last_hide_time)) < TEN_MINS:
				time_remaining = (float(last_hide_time)+TEN_MINS)-time_now
				banned = True
				warned = False
			else:
				#return their integrity since they've served their time
				my_server.hset(hash_name, "tgr", 5)
				banned = False
				time_remaining = 0
				warned = False
		elif integrity < 4:
			##if last_hide_time was 3 mins ago, let the person post, else he's banned
			#re-affirm integrity after serving ban
			if (time_now-float(last_hide_time)) < THREE_MINS:
				time_remaining = (float(last_hide_time)+THREE_MINS)-time_now
				banned = True
				warned = False
			else:
				#return their integrity since they've served their time
				my_server.hset(hash_name, "tgr", 5)
				banned = False
				time_remaining = 0
				warned = False
		elif integrity < 5:
			#not refilling integrity for THREE HOURS, since no punishment was served. Keep the person on thin ice
			if (time_now-float(last_hide_time)) < THREE_HOURS:
				banned = False
				time_remaining = 0
				warned = True
			else:
				#refill integrity after 3 hours of not getting a single hide
				my_server.hset(hash_name, "tgr", 5)
				banned = False
				time_remaining = 0
				warned = False
		else:
			#integrity is refilled after 1 hour of no hide, by default
			if (time_now-float(last_hide_time)) < ONE_HOUR:
				banned = False
				time_remaining = 0
				warned = False
			else:
				my_server.hset(hash_name, "tgr", 5)
				banned = False
				time_remaining = 0
				warned = False
	else:
		banned = False
		time_remaining = 0
		warned = False
	return banned, time_remaining, warned

def document_comment_abuse(user_id):
	my_server = redis.Redis(connection_pool=POOL)
	hash_name = "cah:"+str(user_id) #cah is 'comment abuse hash', it contains latest integrity value
	hash_exists = my_server.exists(hash_name)
	if hash_exists:
		hash_contents = my_server.hgetall(hash_name)
		old_time = hash_contents["t"]
		new_time = time.time()
		time_difference = new_time - float(old_time) #in seconds
		if time_difference < 300.0:
			#update time and integrity
			my_server.hincrby(hash_name, "tgr", amount=-1)
			my_server.hset(hash_name, "t", new_time)
		else:
			#just update the time 
			my_server.hset(hash_name, "t", new_time)
	else:
		mapping = {'t': time.time(), 'tgr':5}
		my_server.hmset(hash_name, mapping)

def publicreply_allowed(user_id):
	my_server = redis.Redis(connection_pool=POOL)
	hash_name = "pah:"+str(user_id)
	hash_exists = my_server.exists(hash_name)
	if hash_exists:
		hash_contents = my_server.hgetall(hash_name)
		last_hide_time = hash_contents["t"]
		integrity = int(hash_contents["tgr"])
		time_now = time.time()
		if integrity < -1:
			if (time_now-float(last_hide_time)) < ONE_DAY:
				time_remaining = (float(last_hide_time)+ONE_DAY)-time_now
				banned = True
				warned = False
			else:
				#return their integrity since they've served their time
				my_server.hset(hash_name, "tgr", 5)
				banned = False
				time_remaining = 0
				warned = False
		elif integrity < 0:
			if (time_now-float(last_hide_time)) < TWELVE_HOURS:
				time_remaining = (float(last_hide_time)+TWELVE_HOURS)-time_now
				banned = True
				warned = False
			else:
				#return their integrity since they've served their time
				my_server.hset(hash_name, "tgr", 5)
				banned = False
				time_remaining = 0
				warned = False
		elif integrity < 1:
			if (time_now-float(last_hide_time)) < SIX_HOURS:
				time_remaining = (float(last_hide_time)+SIX_HOURS)-time_now
				banned = True
				warned = False
			else:
				#return their integrity since they've served their time
				my_server.hset(hash_name, "tgr", 5)
				banned = False
				time_remaining = 0
				warned = False
		elif integrity < 2:
			#if last_vote_time was 1 hour ago, let the person post, else he's banned
			if (time_now-float(last_hide_time)) < ONE_HOUR:
				time_remaining = (float(last_hide_time)+ONE_HOUR)-time_now
				banned = True
				warned = False
			else:
				#return their integrity since they've served their time
				my_server.hset(hash_name, "tgr", 5)
				banned = False
				time_remaining = 0
				warned = False
		elif integrity < 3:
			#if last_vote_time was 10 mins ago, let the person post, else he's banned
			if (time_now-float(last_hide_time)) < TEN_MINS:
				time_remaining = (float(last_hide_time)+TEN_MINS)-time_now
				banned = True
				warned = False
			else:
				#return their integrity since they've served their time
				my_server.hset(hash_name, "tgr", 5)
				banned = False
				time_remaining = 0
				warned = False
		elif integrity < 4:
			##if last_hide_time was 3 mins ago, let the person post, else he's banned
			#re-affirm integrity after serving ban
			if (time_now-float(last_hide_time)) < THREE_MINS:
				time_remaining = (float(last_hide_time)+THREE_MINS)-time_now
				banned = True
				warned = False
			else:
				#return their integrity since they've served their time
				my_server.hset(hash_name, "tgr", 5)
				banned = False
				time_remaining = 0
				warned = False
		elif integrity < 5:
			#not refilling integrity for THREE HOURS, since no punishment was served. Keep the person on thin ice
			if (time_now-float(last_hide_time)) < THREE_HOURS:
				banned = False
				time_remaining = 0
				warned = True
			else:
				#refill integrity after 3 hours of not getting a single hide
				my_server.hset(hash_name, "tgr", 5)
				banned = False
				time_remaining = 0
				warned = False
		else:
			#integrity is refilled after 1 hour of no hide, by default
			if (time_now-float(last_hide_time)) < ONE_HOUR:
				banned = False
				time_remaining = 0
				warned = False
			else:
				my_server.hset(hash_name, "tgr", 5)
				banned = False
				time_remaining = 0
				warned = False
	else:
		banned = False
		time_remaining = 0
		warned = False
	return banned, time_remaining, warned

def document_publicreply_abuse(user_id):
	my_server = redis.Redis(connection_pool=POOL)
	hash_name = "pah:"+str(user_id) #pah is 'publicreply abuse hash', it contains latest integrity value
	hash_exists = my_server.exists(hash_name)
	if hash_exists:
		hash_contents = my_server.hgetall(hash_name)
		old_time = hash_contents["t"]
		new_time = time.time()
		time_difference = new_time - float(old_time) #in seconds
		if time_difference < 300.0:
			#update time and integrity
			my_server.hincrby(hash_name, "tgr", amount=-1)
			my_server.hset(hash_name, "t", new_time)
		else:
			#just update the time 
			my_server.hset(hash_name, "t", new_time)
	else:
		mapping = {'t': time.time(), 'tgr':5}
		my_server.hmset(hash_name, mapping)

def document_nick_abuse(target_id, reporter_id):
	my_server = redis.Redis(connection_pool=POOL)
	hash_name = "nah:"+str(target_id) #nah is 'nick abuse hash', it contains latest integrity value
	#hash_contents = my_server.hgetall(hash_name)
	set_name = "nas:"+str(target_id) #nas is 'nick abuse set', it contains IDs of people who reported this person
	set_exists = my_server.scard(set_name) #returns 0 if nothing exists
	if set_exists:
		if my_server.sismember(set_name, reporter_id):
			#already a member, so don't 'double add'
			return 'Falz'
		else:
			#not a member
			my_server.hincrby(hash_name, "tgr", amount=-1)
			my_server.hset(hash_name, "t", time.time())
			my_server.sadd(set_name, reporter_id)
			return my_server.hget(hash_name, "tgr")
	else:
		mapping = {'t': time.time(), 'tgr':3}
		my_server.hmset(hash_name, mapping)
		my_server.sadd(set_name, reporter_id)
		return my_server.hget(hash_name, "tgr")

def document_link_abuse(user_id):
	my_server = redis.Redis(connection_pool=POOL)
	hash_name = "lah:"+str(user_id)
	hash_exists = my_server.exists(hash_name)
	if hash_exists:
		hash_contents = my_server.hgetall(hash_name)
		old_time = hash_contents["t"]
		new_time = time.time()
		time_difference = new_time - float(old_time) #in seconds
		if time_difference < 60.0:
			#update time and integrity
			my_server.hincrby(hash_name, "tgr", amount=-1)
			my_server.hset(hash_name, "t", new_time)
		else:
			#just update the time 
			my_server.hset(hash_name, "t", new_time)
	else:
		mapping = {'t': time.time(), 'tgr':5}
		my_server.hmset(hash_name, mapping)	

def posting_allowed(user_id):
	my_server = redis.Redis(connection_pool=POOL)
	hash_name = "lah:"+str(user_id)
	hash_exists = my_server.exists(hash_name)
	#ban if the integrity score is too less, and not enough time has passed
	#ban times are warning, 3 mins, 10 mins, 1 hour, 6 hours, 24 hours, 1 week
	if hash_exists:
		hash_contents = my_server.hgetall(hash_name)
		last_vote_time = hash_contents["t"]
		integrity = int(hash_contents["tgr"])
		time_now = time.time()
		if integrity < -6:
			#if last_vote_time was 1 week ago, let the person post, else he's banned
			if (time_now-float(last_vote_time)) < ONE_WEEK:
				time_remaining = (float(last_vote_time)+ONE_WEEK)-time_now
				banned = True
				warned = False
			else:
				#return their integrity since they've served their time
				my_server.hset(hash_name, "tgr", 5)
				banned = False
				time_remaining = 0
				warned = False
		elif integrity < -5:
			#if last_vote_time was 24 hrs ago, let the person post, else he's banned
			if (time_now-float(last_vote_time)) < ONE_DAY:
				time_remaining = (float(last_vote_time)+ONE_DAY)-time_now
				banned = True
				warned = False
			else:
				#return their integrity since they've served their time
				my_server.hset(hash_name, "tgr", 5)
				banned = False
				time_remaining = 0
				warned = False
		elif integrity < -4:
			#if last_vote_time was 24 hrs ago, let the person post, else he's banned
			if (time_now-float(last_vote_time)) < TWELVE_HOURS:
				time_remaining = (float(last_vote_time)+TWELVE_HOURS)-time_now
				banned = True
				warned = False
			else:
				#return their integrity since they've served their time
				my_server.hset(hash_name, "tgr", 5)
				banned = False
				time_remaining = 0
				warned = False
		elif integrity < -3:
			#if last_vote_time was 6 hrs ago, let the person post, else he's banned
			if (time_now-float(last_vote_time)) < SIX_HOURS:
				time_remaining = (float(last_vote_time)+SIX_HOURS)-time_now
				banned = True
				warned = False
			else:
				#return their integrity since they've served their time
				my_server.hset(hash_name, "tgr", 5)
				banned = False
				time_remaining = 0
				warned = False
		elif integrity < -2:
			#if last_vote_time was 1 hour ago, let the person post, else he's banned
			if (time_now-float(last_vote_time)) < ONE_HOUR:
				time_remaining = (float(last_vote_time)+ONE_HOUR)-time_now
				banned = True
				warned = False
			else:
				#return their integrity since they've served their time
				my_server.hset(hash_name, "tgr", 5)
				banned = False
				time_remaining = 0
				warned = False
		elif integrity < -1:
			#if last_vote_time was 10 mins ago, let the person post, else he's banned
			if (time_now-float(last_vote_time)) < TEN_MINS:
				time_remaining = (float(last_vote_time)+TEN_MINS)-time_now
				banned = True
				warned = False
			else:
				#return their integrity since they've served their time
				my_server.hset(hash_name, "tgr", 5)
				banned = False
				time_remaining = 0
				warned = False
		elif integrity < 0:
			##if last_vote_time was 3 mins ago, let the person post, else he's banned
			#re-affirm integrity after serving ban
			if (time_now-float(last_vote_time)) < THREE_MINS:
				time_remaining = (float(last_vote_time)+THREE_MINS)-time_now
				banned = True
				warned = False
			else:
				#return their integrity since they've served their time
				my_server.hset(hash_name, "tgr", 5)
				banned = False
				time_remaining = 0
				warned = False
		elif integrity < 1:
			#not refilling integrity for SIX HOURS, since no punishment was served. Keep the person on thin ice
			if (time_now-float(last_vote_time)) < SIX_HOURS:
				banned = False
				time_remaining = 0
				warned = True
			else:
				#refill integrity after 6 hours of not getting a single downvote
				my_server.hset(hash_name, "tgr", 5)
				banned = False
				time_remaining = 0
				warned = False
		else:
			#integrity is refilled after 1 hour of no downvote, by default
			if (time_now-float(last_vote_time)) < ONE_HOUR:
				banned = False
				time_remaining = 0
				warned = False
			else:
				my_server.hset(hash_name, "tgr", 5)
				banned = False
				time_remaining = 0
				warned = False
	else:
		banned = False
		time_remaining = 0
		warned = False
	return banned, time_remaining, warned

#####################checking image perceptual hashes#####################

def already_exists(photo_hash):
	my_server = redis.Redis(connection_pool=POOL)
	try:
		exists = my_server.zscore("perceptual_hash_set", photo_hash)
		if exists:
			return exists
		else:
			return False
	except:
		return False

def insert_hash(photo_id, photo_hash):
	my_server = redis.Redis(connection_pool=POOL)
	try:
		size = my_server.zcard("perceptual_hash_set")
		limit = 3000
		if size < (limit+1):
			my_server.zadd("perceptual_hash_set", photo_hash, photo_id)
		else:
		   my_server.zremrangebyrank("perceptual_hash_set", 0, (size-limit-1))
		   my_server.zadd("perceptual_hash_set", photo_hash, photo_id)
	except:
		my_server.zadd("perceptual_hash_set", photo_hash, photo_id)