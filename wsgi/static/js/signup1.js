// Determines the time zone of the browser client
document.getElementById("tz").value = jstz.determine().name();

// init telephone # validation
// uses geo-ip to set country.
$("input[type=tel]").intlTelInput({
  utilsScript: "/static/js/intlTelInputUtils.js",
  onlyCountries: ['au', 'nz']
});
