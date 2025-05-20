import 'package:flutter/material.dart';
import 'package:flutter/services.dart' show rootBundle; // For loading local assets
import 'dart:convert'; // For JSON decoding
import 'package:catalog_app/main.dart'; // Ensure CatalogView is imported

// Data model for a Brochure item
// This structure maps directly to the JSON objects in brochures.json
class Brochure {
  final String id; // Unique identifier for the brochure
  final String title; // Title of the brochure (e.g., "Lidl Actual Catalog")
  final String validity; // Validity period (e.g., "May 15, 2025 - May 21, 2025")
  final String thumbnailUrl; // Path to the thumbnail image for the brochure card
  final List<String> catalogPageImages; // List of paths for the full catalog pages

  Brochure({
    required this.id,
    required this.title,
    required this.validity,
    required this.thumbnailUrl,
    required this.catalogPageImages,
  });

  // Factory constructor to create a Brochure object from a JSON Map
  factory Brochure.fromJson(Map<String, dynamic> json) {
    return Brochure(
      id: json['id'] as String,
      title: json['title'] as String,
      validity: json['validity'] as String,
      thumbnailUrl: json['thumbnailUrl'] as String,
      // JSON array of page URLs is converted to a Dart List<String>
      catalogPageImages: List<String>.from(json['pageUrls'] as List),
    );
  }
}

// Main screen widget that displays a list of brochures
class BrochureListScreen extends StatefulWidget {
  const BrochureListScreen({super.key});

  @override
  State<BrochureListScreen> createState() => _BrochureListScreenState();
}

class _BrochureListScreenState extends State<BrochureListScreen> {
  List<Brochure> availableBrochures = []; // List to hold brochure data
  bool isLoading = true; // Flag to show/hide loading indicator
  String? errorMessage; // To store any error messages encountered during data loading

  @override
  void initState() {
    super.initState();
    _loadBrochures(); // Initiate data loading when the screen is initialized
  }

  // Asynchronously loads brochure data from the local JSON asset file
  Future<void> _loadBrochures() async {
    setState(() {
      isLoading = true; // Start loading, show indicator
      errorMessage = null; // Clear any previous error messages
    });
    try {
      // Load the JSON string from the assets folder
      final String response = await rootBundle.loadString('assets/data/brochures.json');
      // Decode the JSON string into a Dart list of dynamic maps
      final List<dynamic> data = json.decode(response);
      // Convert each map in the list to a Brochure object using the factory constructor
      setState(() {
        availableBrochures = data.map((json) => Brochure.fromJson(json)).toList();
        isLoading = false; // Loading finished, hide indicator
      });
    } catch (e) {
      // Catch any errors during loading or parsing
      setState(() {
        errorMessage = 'Failed to load brochures: ${e.toString()}'; // Set error message
        isLoading = false; // Loading finished, hide indicator
      });
      print('Error loading brochures: $e'); // Print error to console for debugging
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Current Brochures'), // App bar title for the brochure list
        centerTitle: true,
        actions: [
          IconButton(
            icon: const Icon(Icons.location_on), // Location icon (Profital-like)
            onPressed: () {
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(content: Text('Location feature coming soon!')),
              );
            },
          ),
        ],
      ),
      body: isLoading // Conditional rendering based on loading state
          ? const Center(child: CircularProgressIndicator()) // Show loading spinner
          : errorMessage != null // If an error occurred
              ? Center(
                  child: Padding(
                    padding: const EdgeInsets.all(16.0),
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Text(
                          errorMessage!, // Display the error message
                          textAlign: TextAlign.center,
                          style: const TextStyle(color: Colors.red, fontSize: 16),
                        ),
                        const SizedBox(height: 16),
                        ElevatedButton(
                          onPressed: _loadBrochures, // Button to retry loading
                          child: const Text('Retry'),
                        ),
                      ],
                    ),
                  ),
                )
              : availableBrochures.isEmpty // If no brochures loaded and no error
                  ? const Center(
                      child: Text(
                        'No brochures available at the moment.', // Message for empty list
                        style: TextStyle(fontSize: 18),
                      ),
                    )
                  : GridView.builder( // Display the grid of brochures
                      padding: const EdgeInsets.all(16.0),
                      gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                        crossAxisCount: 2, // Two columns in the grid
                        crossAxisSpacing: 16.0, // Horizontal spacing between cards
                        mainAxisSpacing: 16.0, // Vertical spacing between cards
                        childAspectRatio: 0.7, // Aspect ratio for each card (height relative to width)
                      ),
                      itemCount: availableBrochures.length, // Number of brochure cards
                      itemBuilder: (context, index) {
                        final brochure = availableBrochures[index];
                        return GestureDetector(
                          onTap: () {
                            // Navigate to CatalogView when a brochure card is tapped
                            Navigator.push(
                              context,
                              MaterialPageRoute(
                                builder: (context) => CatalogView(
                                  catalogTitle: brochure.title,
                                  catalogValidity: brochure.validity,
                                  catalogImages: brochure.catalogPageImages,
                                ),
                              ),
                            );
                          },
                          child: Card(
                            elevation: 4.0, // Shadow effect for the card
                            clipBehavior: Clip.antiAlias, // Ensures content is clipped to card shape
                            shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(10.0), // Rounded corners
                            ),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.stretch,
                              children: [
                                Expanded(
                                  flex: 3, // Thumbnail image takes more space
                                  child: Image.asset(
                                    brochure.thumbnailUrl, // Display brochure thumbnail
                                    fit: BoxFit.cover, // Image fills the available space
                                    errorBuilder: (context, error, stackTrace) {
                                      // Fallback UI if image loading fails
                                      return const Center(child: Icon(Icons.broken_image, size: 40));
                                    },
                                  ),
                                ),
                                Expanded(
                                  flex: 1, // Text content takes less space
                                  child: Padding(
                                    padding: const EdgeInsets.all(8.0),
                                    child: Column(
                                      crossAxisAlignment: CrossAxisAlignment.start,
                                      children: [
                                        Text(
                                          brochure.title,
                                          style: const TextStyle(
                                            fontWeight: FontWeight.bold,
                                            fontSize: 16.0,
                                          ),
                                          maxLines: 1, // Limit title to one line
                                          overflow: TextOverflow.ellipsis, // Add "..." if title overflows
                                        ),
                                        const SizedBox(height: 4.0), // Small vertical space
                                        Text(
                                          brochure.validity,
                                          style: const TextStyle(
                                            fontSize: 12.0,
                                            color: Colors.grey,
                                          ),
                                        ),
                                      ],
                                    ),
                                  ),
                                ),
                              ],
                            ),
                          ),
                        );
                      },
                    ),
      // Bottom navigation bar for app-wide navigation (Profital-like)
      bottomNavigationBar: BottomNavigationBar(
        items: const [
          BottomNavigationBarItem(
            icon: Icon(Icons.home),
            label: 'Home',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.favorite_border),
            label: 'Favorites',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.bookmark_border),
            label: 'Bookmarks',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.message),
            label: 'Messages',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.person),
            label: 'Profile',
          ),
        ],
        selectedItemColor: Colors.red, // Color for the selected icon
        unselectedItemColor: Colors.grey, // Color for unselected icons
        type: BottomNavigationBarType.fixed, // Distributes items evenly
        onTap: (index) {
          // Placeholder for navigation logic (e.g., using a PageView for screens)
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('Navigating to ${['Home', 'Favorites', 'Bookmarks', 'Messages', 'Profile'][index]}')),
          );
        },
      ),
    );
  }
}