// set timezone based on browser time
var date = new Date( );
document.getElementById("tz").value = date.getTimezoneOffset( ) / 60;

// init telephone # validation
// uses geo-ip to set country.

var telInput = $("#tel");
var emailInput = $("#email");

var phoneInvalid = document.getElementById("tel-invalid");
var telExists = document.getElementById("tel-exists");
var emailExists = document.getElementById("email-exists");

telInput.intlTelInput({
  defaultCountry: "auto",
  utilsScript: "/static/js/intlTelInputUtils.js"
});

// on blur: validate telephone #
telInput.blur(function() {
  if ($.trim(telInput.val())) {
    if (telInput.intlTelInput("isValidNumber")) {
      phoneInvalid.classList.add('hide');

      var sTel = telInput.val().replace(/[^a-zA-Z0-9\+]/gi, '');
      console.log(sTel);
      checkT(sTel);

    } else {
        document.getElementById('submit').disabled = true;
        phoneInvalid.classList.remove('hide');
      }
  } else {
      //document.getElementById('submit').disabled = true;
      phoneInvalid.classList.remove('hide');
    }
});

// on keydown: reset tel input
telInput.keydown(function() {
  phoneInvalid.classList.add('hide');
  telExists.classList.add('hide');
});

telInput.on("invalidkey", function() {
  telInput.addClass("flash");
  setTimeout(function() {
    telInput.removeClass("flash");
  }, 100);
});

// on blur: check email address
emailInput.blur(function() {
  console.log( $.trim(emailInput.val()) );
  checkE( $.trim(emailInput.val()) );
});

// on keyboard: reset email input
emailInput.keydown(function() {
  emailExists.classList.add('hide');
});

function checkT(x) {
  var api = "http://localhost:5000/user";
  $.getJSON(api, {
    id: x
  })
  .done(function( data ) {
    console.log("player found: ", data);
    telExists.classList.remove('hide');

    // disable submit button
    document.getElementById('submit').disabled = true;
  })
  .fail(function() {
    console.log( "no player found / error" );
    telExists.classList.add('hide');

    // enable submit button
    document.getElementById('submit').disabled = false;
  });
}

function checkE(x) {
  var api = "http://localhost:5000/user";
  $.getJSON(api, {
    id: x
  })
  .done(function( data ) {
    console.log("player found: ", data);
    emailExists.classList.remove('hide');

    // disable submit button
    document.getElementById('submit').disabled = true;
  })
  .fail(function() {
    console.log( "no player found / error" );
    emailExists.classList.add('hide');

    // enable submit button
    document.getElementById('submit').disabled = false;
  });
}
