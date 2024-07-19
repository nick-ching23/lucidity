// Function to search for stock symbols

        // Function to display search results
        function displayResults(results) {
            const resultsContainer = document.getElementById('search-results');
            resultsContainer.innerHTML = '';

            if (!results || results.length === 0) {
                resultsContainer.innerHTML = '<p>No results found</p>';
                return;
            }

            results.forEach(result => {
                const div = document.createElement('div');
                div.textContent = `${result['1. symbol']} - ${result['2. name']}`;
                div.addEventListener('click', () => {
                    document.getElementById('search-input').value = result['1. symbol'];
                    resultsContainer.innerHTML = '';
                });
                resultsContainer.appendChild(div);
            });
        }

        // Function to fetch and display stock data
        async function fetchStockData() {
            try {
                const response = await fetch('/data');
                if (!response.ok) {
                    throw new Error('Network response was not ok ' + response.statusText);
                }
                const data = await response.json();
                displayStockData(data);
            } catch (error) {
                console.error('Error fetching data:', error);
            }
        }

        // Fetch news data and display in grid
        async function fetchNews() {
            try {
                const response = await fetch(`/fetch-news`);
                const data = await response.json();
                displayNews(data.feed.slice(0, 6)); // Only display top 6 news articles
            } catch (error) {
                console.error('Error fetching news:', error);
            }
        }

        // Function to display news in a grid layout
        function displayNews(newsItems) {
            const newsContainer = document.getElementById('news-container');
            newsContainer.innerHTML = '';

            newsItems.forEach(item => {
                const newsDiv = document.createElement('div');
                newsDiv.classList.add('news-item');
                newsDiv.innerHTML = `
                    <img src="${item.banner_image || 'placeholder.jpg'}" alt="News Image">
                    <div class="title"><a href="${item.url}" target="_blank">${item.title}</a></div>
                    <div class="description">${item.summary}</div>
                    <div class="sentiment">Sentiment: ${item.overall_sentiment_score}</div>
                `;
                newsContainer.appendChild(newsDiv);
            });
        }

        // Function to display stock data
        function displayStockData(data) {
            const labels = data.map(item => new Date(item.index));
            const prices = data.map(item => item.close);

            // Destroy existing chart instance if it exists
            if (window.stockChart && typeof window.stockChart.destroy === 'function') {
                window.stockChart.destroy();
            }

            const ctx = document.getElementById('stockChart').getContext('2d');
            window.stockChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [{
                        label: 'Close Price',
                        data: prices,
                        borderColor: 'rgba(75, 192, 192, 1)',
                        backgroundColor: 'rgba(75, 192, 192, 0.2)',
                        fill: true,
                        borderWidth: 1,
                        pointRadius: 2  // Increase point radius for better visibility
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false, // Allow the chart to fit its container
                    scales: {
                        x: {
                            type: 'time',
                            time: {
                                unit: 'day', // Change to 'day' to handle daily data
                                tooltipFormat: 'MM/dd/yyyy', // Format for the tooltip
                                displayFormats: {
                                    day: 'MM/dd/yyyy' // Format for the display
                                }
                            },
                            title: {
                                display: true,
                                text: 'Date'
                            }
                        },
                        y: {
                            beginAtZero: false,
                            title: {
                                display: true,
                                text: 'Price (USD)'
                            }
                        }
                    },
                    plugins: {
                        legend: {
                            display: true,
                            position: 'top'
                        }
                    }
                }
            });
        }

        document.addEventListener('DOMContentLoaded', function () {
            console.log('DOM fully loaded and parsed');
            fetchStockData();
            fetchNews();

            // Attach event listener to search input
            document.getElementById('search-input').addEventListener('input', searchSymbols);
        });