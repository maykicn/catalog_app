import 'package:flutter/material.dart';

void main() {
  // The main function that starts the app
  runApp(const MyApp());
}

// The top-level widget of the application
class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Profital Clone MVP', // App title
      theme: ThemeData(
        primarySwatch: Colors.blue, // Primary color palette for the app
        appBarTheme: const AppBarTheme(
          backgroundColor: Colors.red, // AppBar color (Lidl-like)
          foregroundColor: Colors.white, // AppBar text color
        ),
      ),
      home: const CatalogView(), // Our main screen will now be CatalogView
      debugShowCheckedModeBanner: false, // Removes the debug banner
    );
  }
}

// Main widget to display catalogs
class CatalogView extends StatefulWidget {
  const CatalogView({super.key});

  @override
  _CatalogViewState createState() => _CatalogViewState();
}

class _CatalogViewState extends State<CatalogView> {
  // List of catalog image paths, hardcoded for now.
  // Make sure these paths match your actual image files in assets/lidl_catalog/
  final List<String> catalogImages = [
    'assets/lidl_catalog/page_01.jpg',
    'assets/lidl_catalog/page_02.jpg',
    'assets/lidl_catalog/page_03.jpg', 
    'assets/lidl_catalog/page_04.jpg',
    'assets/lidl_catalog/page_05.jpg',
    'assets/lidl_catalog/page_06.jpg',
    'assets/lidl_catalog/page_07.jpg',
    'assets/lidl_catalog/page_08.jpg',
    'assets/lidl_catalog/page_09.jpg',
    'assets/lidl_catalog/page_10.jpg',
  ];
  final String catalogTitle = 'Lidl Aktüel Katalog'; // Can be changed
  final String catalogValidity = '15.05.2025 - 21.05.2025'; // Replace with actual dates
  int currentPage = 0; // Current page number

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(catalogTitle), // Use the defined title
        centerTitle: true,
      ),
      body: Column(
        children: [
          Expanded(
            child: PageView.builder(
              // If no images are added yet, show a warning, otherwise use catalogImages.length
              itemCount: catalogImages.isNotEmpty ? catalogImages.length : 1, // Number of images
              onPageChanged: (index) {
                setState(() {
                  currentPage = index;
                });
              },
              itemBuilder: (context, index) {
                if (catalogImages.isEmpty) {
                  return const Center(
                    child: Text(
                      'Catalog images are loading or not yet added. '
                      'Please add images to the assets folder.',
                      textAlign: TextAlign.center,
                      style: TextStyle(fontSize: 18),
                    ),
                  );
                }
                return Image.asset(
                  catalogImages[index], // Load image from assets
                  fit: BoxFit.contain, // Ensures the image fits the screen
                );
              },
            ),
          ),
          // Page number indicator
          Padding(
            padding: const EdgeInsets.all(8.0),
            child: Text(
              catalogImages.isNotEmpty
                  ? 'Page ${currentPage + 1} / ${catalogImages.length}'
                  : 'Loading Catalog...',
              style: const TextStyle(fontSize: 16),
            ),
          ),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 8.0, vertical: 4.0),
            child: Text(
              'Validity: $catalogValidity',
              style: const TextStyle(fontSize: 14, color: Colors.grey),
            ),
          ),
        ],
      ),
    );
  }
}