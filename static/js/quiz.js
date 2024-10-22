document.addEventListener("DOMContentLoaded", function() {
    // Enable Next button on radio selection for each question modal
    const forms = document.querySelectorAll("form[id^='form-']");
    
    forms.forEach((form, index) => {
        if (index + 1 === 10) return;  // Skip Modal 10 logic
        
        const nextButton = document.querySelector(`.next-button-${index + 1}`);
        
        // Add a check to see if nextButton exists
        if (!nextButton) {
            console.error(`No next button found for .next-button-${index + 1}`);
            return;  // Stop this iteration if no button is found
        }
    
        // Enable the "Next" button when a radio button is selected
        form.addEventListener('change', function() {
            if (form.querySelector('input[type="radio"]:checked')) {
                nextButton.disabled = false;  // Enable the "Next" button
            }
        });
            
    });
        
    // Enable "Show Results" button in the last modal
    const showResultsButton = document.querySelector('.show-results-button');
    const lastForm = document.getElementById('form-10');
    lastForm.addEventListener('change', function() {
      if (lastForm.querySelector('input[type="radio"]:checked')) {
        showResultsButton.disabled = false;
      }
    });
  
    // Persona score calculation
    let personaScores = {
      jill: 0,
      olivia: 0,
      max: 0,
      zee: 0,
      dante: 0,
      buddy: 0,
      arlo: 0,
      sophia: 0,
      frank: 0,
      leo: 0,
      alex: 0
    };
  
    let visualScore = 0;
    let minimalistScore = 0;
  
    // Calculate persona scores based on answers
    function calculateScores() {
      const answers = {
        question1: document.querySelector('input[name="question1"]:checked').value,
        question2: document.querySelector('input[name="question2"]:checked').value,
        question3: document.querySelector('input[name="question3"]:checked').value,
        question4: document.querySelector('input[name="question4"]:checked').value,
        question5: document.querySelector('input[name="question5"]:checked').value,
        question6: document.querySelector('input[name="question6"]:checked').value,
        question7: document.querySelector('input[name="question7"]:checked').value,
        question8: document.querySelector('input[name="question8"]:checked').value,
        question9: document.querySelector('input[name="question9"]:checked').value,
        question10: document.querySelector('input[name="question10"]:checked').value,
      };
  
      // Scoring logic for each question
      // Question 1: Ideal weekend activity
      if (answers.question1 === "1") { // Keeping up with trends
        personaScores.zee += 10;
        visualScore += 2;
      } else if (answers.question1 === "2") { // Personal project
        personaScores.olivia += 10;
        minimalistScore += 2;
      } else if (answers.question1 === "3") { // Relaxing with a book
        personaScores.sean += 10;
      } else if (answers.question1 === "4") { // Reflecting with loved ones
        personaScores.frank += 10;
        minimalistScore += 2;
      }
  
      // Question 2: Preferred Communication Style
      if (answers.question2 === "1") { // Playfulness and energy
        personaScores.max += 10;
        visualScore += 2;
      } else if (answers.question2 === "2") { // Clear and direct
        personaScores.olivia += 10;
        minimalistScore += 2;
      } else if (answers.question2 === "3") { // Friendly and supportive
        personaScores.grace += 10;
      } else if (answers.question2 === "4") { // Thoughtful advice
        personaScores.frank += 10;
      }
  
      // Question 3: Humor and Seriousness
      if (answers.question3 === "1") { // Fun with humor
        personaScores.max += 10;
        visualScore += 2;
      } else if (answers.question3 === "2") { // Balance of humor and focus
        personaScores.zee += 10;
      } else if (answers.question3 === "3") { // Serious and focused
        personaScores.olivia += 10;
        minimalistScore += 2;
      }
  
      // Question 4: Technology Comfort Level
      if (answers.question4 === "1") { // Love new tech
        personaScores.zee += 10;
        visualScore += 3;
      } else if (answers.question4 === "2") { // Comfortable but simple
        personaScores.jill += 10;
      } else if (answers.question4 === "3") { // Avoid tech
        personaScores.leo += 10;
        minimalistScore += 3;
      }
  
      // Question 5: Emotional Support vs. Task Efficiency
      if (answers.question5 === "1") { // Emotional support
        personaScores.sophia += 15;
        visualScore += 2;
      } else if (answers.question5 === "2") { // Balance of both
        personaScores.jill += 15;
      } else if (answers.question5 === "3") { // Task-driven
        personaScores.olivia += 15;
        minimalistScore += 2;
      }
  
      // Question 6: Reaction to Stressful Situations
      if (answers.question6 === "1") { // Laugh it off
        personaScores.max += 15;
      } else if (answers.question6 === "2") { // Stay calm and break tasks down
        personaScores.sean += 15;
      } else if (answers.question6 === "3") { // Find practical solutions
        personaScores.olivia += 15;
        minimalistScore += 2;
      } else if (answers.question6 === "4") { // Seek wisdom or guidance
        personaScores.frank += 15;
      }
  
      // Question 7: Creative vs. Practical Thinking
      if (answers.question7 === "1") { // Love creativity
        personaScores.arlo += 10;
        visualScore += 3;
      } else if (answers.question7 === "2") { // Balance creativity with structure
        personaScores.max += 10;
      } else if (answers.question7 === "3") { // Practical
        personaScores.olivia += 10;
        minimalistScore += 3;
      }
  
      // Question 8: Personality Compatibility
      if (answers.question8 === "1") { // Energetic and outgoing
        personaScores.dante += 15;
        visualScore += 2;
      } else if (answers.question8 === "2") { // Calm and steady
        personaScores.sean += 15;
      } else if (answers.question8 === "3") { // Nurturing and supportive
        personaScores.sophia += 15;
      } else if (answers.question8 === "4") { // Logical and analytical
        personaScores.olivia += 15;
        minimalistScore += 2;
      }
  
      // Question 9: Inclusivity and Diversity
      if (answers.question9 === "1") { // Thrive in diverse environments
        personaScores.zee += 10;
        visualScore += 2;
      } else if (answers.question9 === "2") { // Open but prefer familiar
        personaScores.buddy += 10;
      } else if (answers.question9 === "3") { // Prefer focused approach
        personaScores.alex += 10;
        minimalistScore += 2;
      }
  
      // Question 10: Long-term goals
      if (answers.question10 === "1") { // Detailed plans
        personaScores.olivia += 15;
        minimalistScore += 2;
      } else if (answers.question10 === "2") { // Flexible with creativity
        personaScores.arlo += 15;
        visualScore += 3;
      } else if (answers.question10 === "3") { // Focus on big picture
        personaScores.leo += 15;
      } else if (answers.question10 === "4") { // Take things day by day
        personaScores.max += 15;
      }
  
      // Determine UI mode
      const uiMode = visualScore > minimalistScore ? 'fancy' : 'simple';
      
      // Update UI mode in database
      $.ajax({
        url: '/update_preferences',
        type: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({
          UImode: uiMode
        }),
        success: function(response) {
          console.log('UImode updated successfully:', uiMode);
        },
        error: function(error) {
          console.log('Error updating UImode:', error);
        }
      });
      
      return personaScores;
    }
  
    // Get recommended personas and display them
    function getRecommendedPersonas() {
      const sortedPersonas = Object.keys(personaScores).sort((a, b) => personaScores[b] - personaScores[a]);
      return sortedPersonas.slice(0, 3); // Return the top 3 personas
    }
  
    function generateRecommendations() {
        // Fetch the UImode from the database or session
        $.ajax({
          url: '/get_preferences',  // Endpoint to get the current UImode and other preferences
          type: 'GET',
          success: function(response) {
            const uiMode = response.UImode;  // Extract UImode from the server response
            const recommendedPersonas = getRecommendedPersonas();  // Function to calculate recommended personas
            const recommendationsDiv = document.getElementById('modal-12-recommendations');
            
            recommendationsDiv.innerHTML = '';  // Clear previous recommendations
      
            // Iterate over the recommended personas and generate the options
            recommendedPersonas.forEach(persona => {
              // Set the image path based on UImode
              const imagePath = (uiMode === 'simple') 
                ? '/static/img/personas/generic.png'  // Use generic image for "simple" mode
                : '/static/img/personas/${persona}.png';  // Use persona-specific image for "fancy" mode
      
              // Generate the HTML for the persona option
              const personaOption = `
                <label>
                  <input type="radio" name="persona" value="${persona}">
                  <img src="${imagePath}" alt="${persona}" class="persona-img">
                  ${persona.charAt(0).toUpperCase() + persona.slice(1)}
                </label>
              `;
      
              // Append the generated option to the recommendations div
              recommendationsDiv.innerHTML += personaOption;
            });
      
            // Enable the confirm button when a persona is selected
            recommendationsDiv.addEventListener('change', function() {
              document.querySelector('.confirm-button').disabled = false;
            });
          },
          error: function(error) {
            console.log('Error fetching preferences:', error);
          }
        });
      }      
  
    // Show results button handler
    document.querySelector('.show-results-button').addEventListener('click', function() {
      // Step 1: Calculate the scores
      calculateScores(); 
      
      // Step 2: Generate recommendations and populate modal-12
      generateRecommendations(); 
      
      // Step 3: Open the results modal
      const resultsModal = new bootstrap.Modal(document.getElementById('modal-quizResults'));
      resultsModal.show();
    });
  
    // Confirm persona and update the database
    document.querySelector('.confirm-button').addEventListener('click', function() {
        // Get the selected persona from the radio button group
        const selectedPersona = document.querySelector('input[name="persona"]:checked').value;
      
        // Make an AJAX POST request to update the CurrentPersona in the database
        $.ajax({
          url: '/update_preferences',
          type: 'POST',
          contentType: 'application/json',  // Ensure we're sending JSON data
          data: JSON.stringify({            // Send the selected persona in JSON format
            CurrentPersona: selectedPersona
          }),
          success: function(response) {
            console.log('Persona updated successfully:', selectedPersona);
            // Close the modal after confirmation
            $('#modal-quizResults').modal('hide');
          },
          error: function(error) {
            console.log('Error updating persona:', error);
          }
        });
      });

  });
  