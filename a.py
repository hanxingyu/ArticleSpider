import re

match_re = re.match('.*?(\d+).*', 'f432423dsjaj')
print(match_re.group(1))
print(match_re.group(0))
# if match_re:
#     nums = int(match_re.group(1))
# else:
#     nums = 0
# print(nums)