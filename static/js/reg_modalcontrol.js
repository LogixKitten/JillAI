// Function to capture the first name from modal-1 and store it in localStorage
function captureName() {
    const firstName = document.getElementById('firstNameInput').value;
    if (firstName) {
        // Store the first name in localStorage
        localStorage.setItem('firstName', firstName);
    }
}

// Function to dynamically replace <firstName> in the modal content
function populateNameInModal(modalId) {
    const firstName = localStorage.getItem('firstName');
    if (firstName) {
        const modal = document.getElementById(modalId);
        const modalBody = modal.querySelector('.modal-body').innerHTML;
        // Replace all occurrences of <firstName> with the actual firstName
        modal.querySelector('.modal-body').innerHTML = modalBody.replace(/<firstName>/g, firstName);
    }
}

// Event listener for when modal-1's "Next" button is clicked
document.querySelector('#modal-1 .btn-primary').addEventListener('click', function() {
    captureName();
});

// Event listeners to populate the name in modal-2, modal-3, and modal-4
document.querySelector('#modal-2').addEventListener('show.bs.modal', function() {
    populateNameInModal('modal-2');
});

document.querySelector('#modal-3').addEventListener('show.bs.modal', function() {
    populateNameInModal('modal-3');
});

document.querySelector('#modal-4').addEventListener('show.bs.modal', function() {
    populateNameInModal('modal-4');
});
