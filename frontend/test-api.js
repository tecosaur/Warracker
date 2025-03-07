// API connection test script
document.addEventListener('DOMContentLoaded', function() {
    // Element to display test results
    const resultElement = document.getElementById('apiTestResult');
    
    if (resultElement) {
        resultElement.innerHTML = '<p>Checking API connection...</p>';
        
        // Test API connection
        fetch('/api/warranties')
            .then(response => {
                if (!response.ok) {
                    throw new Error('API responded with status: ' + response.status);
                }
                return response.json();
            })
            .then(data => {
                console.log('API response:', data);
                resultElement.innerHTML = `
                    <div class="alert alert-success">
                        <h4>✅ API Connection Successful</h4>
                        <p>The API responded with ${data && Array.isArray(data) ? data.length : 0} warranties.</p>
                        <pre>${JSON.stringify(data && data.length ? data[0] : {}, null, 2)}</pre>
                    </div>
                `;
            })
            .catch(error => {
                console.error('API connection error:', error);
                resultElement.innerHTML = `
                    <div class="alert alert-danger">
                        <h4>❌ API Connection Failed</h4>
                        <p>Error: ${error.message}</p>
                        <h5>Debug Information:</h5>
                        <ul>
                            <li>Browser URL: ${window.location.href}</li>
                            <li>Target API: /api/warranties</li>
                            <li>Make sure the backend is running and accessible</li>
                            <li>Check that nginx is properly configured to proxy API requests</li>
                        </ul>
                    </div>
                `;
            });
    }
}); 