from osc import OSC
osc = OSC()
osc.periodicty = osc.MINUTELY
#ret = osc.get_changes_since(1)
test = osc.get_sequence_number("2012-09-12 09:12:17")
print(test)
