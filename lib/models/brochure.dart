import 'package:cloud_firestore/cloud_firestore.dart';

class Brochure {
  final String id;
  final String marketName;
  final String title;
  final String validity;
  // Field name updated to match Firestore
  final String thumbnail; 
  // Field name updated to match Firestore
  final List<String> pages; 
  final Timestamp timestamp;

  Brochure({
    required this.id,
    required this.marketName,
    required this.title,
    required this.validity,
    required this.thumbnail, 
    required this.pages, 
    required this.timestamp,
  });

  // Factory constructor to create a Brochure object from a Firestore DocumentSnapshot
  factory Brochure.fromFirestore(DocumentSnapshot doc) {
    Map<String, dynamic> data = doc.data() as Map<String, dynamic>;
    return Brochure(
      id: doc.id, // Document ID
      marketName: data['marketName'] ?? 'Unknown Market', // marketName from Firestore
      title: data['title'] ?? 'Unknown Title',
      validity: data['validity'] ?? 'No Validity',
      thumbnail: data['thumbnail'] ?? '', 
      pages: List<String>.from(data['pages'] ?? []), // 'pages' from Firebase
      timestamp: data['timestamp'] as Timestamp, // 'timestamp' from Firebase
    );
  }
}
