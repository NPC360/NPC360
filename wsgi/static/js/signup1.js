// set timezone based on browser time
var date = new Date( );
document.getElementById("tz").value = date.getTimezoneOffset( ) / 60;
