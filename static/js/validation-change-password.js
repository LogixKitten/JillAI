function togglePassword(inputId, iconId) {
    const passwordInput = document.getElementById(inputId);
    const passwordIcon = document.getElementById(iconId);

    if (passwordInput.type === 'password') {
        passwordInput.type = 'text';
        passwordIcon.src = 'static/img/icons/eye-password-view.svg'; // Show password icon
    } else {
        passwordInput.type = 'password';
        passwordIcon.src = 'static/img/icons/eye-password-hide.svg'; // Hide password icon
    }
}

// Attach togglePassword function to all password fields
document.getElementById('togglePasswordBtn1').onclick = function () {
    togglePassword('currentPassword', 'passwordIcon1');
};
document.getElementById('togglePasswordBtn2').onclick = function () {
    togglePassword('newPassword', 'passwordIcon2');
};
document.getElementById('togglePasswordBtn3').onclick = function () {
    togglePassword('confirmPassword', 'passwordIcon3');
};


// Show and hide password requirements
function showRequirements(requirementsId) {
    document.getElementById(requirementsId).style.display = 'block';
}

function hideRequirements(requirementsId) {
    document.getElementById(requirementsId).style.display = 'none';
}

// Validate individual password field
function validatePasswordField(passwordId, requirementsId, successMessageId) {
    const password = document.getElementById(passwordId).value;
    const requirementsBox = document.getElementById(requirementsId);
    const successMessage = document.getElementById(successMessageId);

    const minLength = password.length >= 8;
    const uppercase = /[A-Z]/.test(password);
    const lowercase = /[a-z]/.test(password);
    const number = /\d/.test(password);
    const specialChar = /[@$!%*?&]/.test(password);

    requirementsBox.querySelector('#minLength').classList.toggle('valid', minLength);
    requirementsBox.querySelector('#uppercase').classList.toggle('valid', uppercase);
    requirementsBox.querySelector('#lowercase').classList.toggle('valid', lowercase);
    requirementsBox.querySelector('#number').classList.toggle('valid', number);
    requirementsBox.querySelector('#specialChar').classList.toggle('valid', specialChar);

    if (minLength && uppercase && lowercase && number && specialChar) {
        successMessage.style.display = 'block';
    } else {
        successMessage.style.display = 'none';
    }
}

// Validate password confirmation
function validatePasswordMatch(newPasswordId, confirmPasswordId, requirementsId) {
    const newPassword = document.getElementById(newPasswordId).value;
    const confirmPassword = document.getElementById(confirmPasswordId).value;
    const requirementsBox = document.getElementById(requirementsId);

    const match = newPassword === confirmPassword;
    requirementsBox.querySelector('#matchNewPassword').classList.toggle('valid', match);
}

// Attach event listeners to the inputs
document.addEventListener('DOMContentLoaded', function () {
    const currentPasswordField = document.getElementById('currentPassword');
    const newPasswordField = document.getElementById('newPassword');
    const confirmPasswordField = document.getElementById('confirmPassword');

    currentPasswordField.addEventListener('focus', () => showRequirements('passwordRequirements1'));
    currentPasswordField.addEventListener('blur', () => hideRequirements('passwordRequirements1'));
    currentPasswordField.addEventListener('input', () =>
        validatePasswordField('currentPassword', 'passwordRequirements1', 'passwordSuccessMessage1')
    );

    newPasswordField.addEventListener('focus', () => showRequirements('passwordRequirements2'));
    newPasswordField.addEventListener('blur', () => hideRequirements('passwordRequirements2'));
    newPasswordField.addEventListener('input', () => {
        validatePasswordField('newPassword', 'passwordRequirements2', 'passwordSuccessMessage2');
        validatePasswordMatch('newPassword', 'confirmPassword', 'passwordRequirements3');
    });

    confirmPasswordField.addEventListener('focus', () => showRequirements('passwordRequirements3'));
    confirmPasswordField.addEventListener('blur', () => hideRequirements('passwordRequirements3'));
    confirmPasswordField.addEventListener('input', () => {
        validatePasswordField('confirmPassword', 'passwordRequirements3', 'passwordSuccessMessage3');
        validatePasswordMatch('newPassword', 'confirmPassword', 'passwordRequirements3')
    });
});
