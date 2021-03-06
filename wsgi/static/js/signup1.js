// Determines the time zone of the browser client
$("#tz").each(function() {
	this.value = jstz.determine().name();
});

// init telephone # validation
// uses geo-ip to set country.
$("input[type=tel]").intlTelInput({
  utilsScript: "http://npc360a-nealrs.rhcloud.com/static/js/intlTelInputUtils.js",
  onlyCountries: ['au', 'nz', 'us', 'ca']
});
