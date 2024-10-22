document.addEventListener('DOMContentLoaded', function() {
    // Check if we need to show the first login modal
    if (sessionStorage.getItem('showFirstLoginModal') === 'true') {
      // Trigger the modal (assuming Bootstrap modal)
      const firstLoginModal = new bootstrap.Modal(document.getElementById('modal-personality_quiz_start'));
      firstLoginModal.show();
  
      // Remove the flag from sessionStorage to avoid showing it again
      sessionStorage.removeItem('showFirstLoginModal');
    }
  });
  