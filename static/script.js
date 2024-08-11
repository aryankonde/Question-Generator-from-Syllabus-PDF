document.getElementById('syllabus-form').addEventListener('submit', function(event) {
    event.preventDefault(); // Prevent the default form submission

    const formData = new FormData(this); // Create a FormData object from the form

    fetch('/generate-questions', {
        method: 'POST',
        body: formData // Send the form data
    })
    .then(response => {
        // Check if the response is okay (status in the range 200-299)
        if (!response.ok) {
            throw new Error('Network response was not ok: ' + response.statusText);
        }
        return response.json(); // Parse the response as JSON
    })
    .then(data => {
        // Check if the data contains the "questions" key
        if (data.questions && Array.isArray(data.questions)) {
            // Display the generated questions
            const questionsList = data.questions.map(question => `<li>${question}</li>`).join('');
            document.getElementById('results').innerHTML = `<ol>${questionsList}</ol>`;
            
            // Enable the "Generate Papers" button
            document.getElementById('generate-papers').disabled = false;
        } else {
            // Handle unexpected response format
            document.getElementById('results').innerHTML = "Error: Unexpected response format.";
        }
    })
    .catch(error => {
        // Handle any errors that occurred during the fetch
        console.error('Error:', error);
        document.getElementById('results').innerHTML = "An error occurred: " + error.message; // Display the error message
    });
});

document.getElementById('generate-papers').addEventListener('click', function() {
    this.disabled = true; // Disable the button to prevent multiple clicks

    fetch('/generate-papers')
    .then(response => {
        // Check if the response is okay (status in the range 200-299)
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        return response.json();
    })
    .then(data => {
        // Check if the data contains the "message" key
        if (data.message) {
            // Generate download links for the question papers
            const downloadLinksDiv = document.getElementById('download-links');
            downloadLinksDiv.innerHTML = ''; // Clear previous links
            for (let i = 1; i <= 10; i++) {
                const link = document.createElement('a');
                link.href = `/download/question_paper_${i}.pdf`; // Change to .pdf for PDF files
                link.textContent = `Download Question Paper ${i}`;
                link.download = `question_paper_${i}.pdf`; // Change to .pdf for PDF files
                downloadLinksDiv.appendChild(link);
                downloadLinksDiv.appendChild(document.createElement('br'));
            }
        } else {
            // Handle unexpected response format
            document.getElementById('results').innerHTML = "Error: Unexpected response format.";
        }
    })
    .catch(error => {
        // Handle any errors that occurred during the fetch
        console.error('Error:', error);
        document.getElementById('generate-papers').disabled = false; // Re-enable the button on error
    });
});