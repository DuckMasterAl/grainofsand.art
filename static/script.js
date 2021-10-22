window.onload = function() {
  if (document.getElementsByClassName('footer_date')[0] != undefined) {
    const date = new Date().getFullYear()
    document.getElementsByClassName('footer_date')[0].innerHTML = date + ' ';
  }
  document.body.style.visibility = 'visible';
}

async function submitCommissionForm() {
  document.getElementById('form-error').style.display = 'none';
  const formValue = document.getElementById('short-description').value;
  if (formValue == '') {
    document.getElementById('form-error').innerHTML = 'No description was provided.';
    document.getElementById('form-error').style.display = 'block';
    return
  }
  var response = await fetch('api/submit-commission', {
    method: 'POST',
    body: JSON.stringify({"description": formValue})
  });
  if (response.status === 200) {
    document.getElementById('actual-form').style.display = 'none';
    document.getElementById('success-form').style.display = 'block';
  }
  else if (response.status == 401) {
    document.getElementById('form-error').innerHTML = 'You must <a href="/discord" target="_blank">join our discord</a> to make a commission.';
    document.getElementById('form-error').style.display = 'block';
  }
  else {
    document.getElementById('form-error').innerHTML = 'Invalid server response. Please let us know about this in our discord.';
    document.getElementById('form-error').style.display = 'block';
  }
}

async function removeImage(object) {
  var response = await fetch('api/admin-image', {
    method: 'DELETE',
    body: JSON.stringify({"image": object.innerHTML})
  });
  if (response.status === 200) {
    object.remove()
    alert("poof! it gone.")
  }
  else {
    alert("something went wrong e.e");
  }
}

function adminFormSubmit() {
  window.onbeforeunload = function() {};
  document.getElementById('submit-button').disabled = true;
  document.getElementById('submit-button').backgroundColor = "grey";
}
