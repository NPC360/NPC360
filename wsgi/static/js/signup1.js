// set timezone based on browser time
var date = new Date( );
document.getElementById("tz").value = date.getTimezoneOffset( ) / 60;

// init telephone # validation
// uses geo-ip to set country.

var telInput = $("#tel"),
errorMsg = $("#error-msg"),
validMsg = $("#valid-msg");

telInput.intlTelInput({
  defaultCountry: "auto",
  utilsScript: "/static/js/intlTelInputUtils.js"
  //
});

// on blur: validate
telInput.blur(function() {
  if ($.trim(telInput.val())) {
    if (telInput.intlTelInput("isValidNumber")) {
      validMsg.removeClass("hide");
    } else {
      telInput.addClass("error");
      errorMsg.removeClass("hide");
      validMsg.addClass("hide");
    }
  }
});

// on keydown: reset
telInput.keydown(function() {
  telInput.removeClass("error");
  errorMsg.addClass("hide");
  validMsg.addClass("hide");
});

telInput.on("invalidkey", function() {
  telInput.addClass("flash");
  setTimeout(function() {
    telInput.removeClass("flash");
  }, 100);
});
