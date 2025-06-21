import 'package:cloud_firestore/cloud_firestore.dart';

class Brochure {
  final String id;
  final String marketName;
  final String title;
  final String validity;
  final String thumbnail; 
  final List<String> pages; 
  final Timestamp timestamp;
  final String weekType; // <<< NEW FIELD

  Brochure({
    required this.id,
    required this.marketName,
    required this.title,
    required this.validity,
    required this.thumbnail, 
    required this.pages, 
    required this.timestamp,
    required this.weekType, // <<< ADDED TO CONSTRUCTOR
  });

  // Factory constructor to create a Brochure object from a Firestore DocumentSnapshot
  factory Brochure.fromFirestore(DocumentSnapshot doc) {
    Map<String, dynamic> data = doc.data() as Map<String, dynamic>;
    return Brochure(
      id: doc.id,
      marketName: data['marketName'] ?? 'Unknown Market',
      title: data['title'] ?? 'Unknown Title',
      validity: data['validity'] ?? 'No Validity',
      thumbnail: data['thumbnail'] ?? '', 
      pages: List<String>.from(data['pages'] ?? []),
      timestamp: data['timestamp'] as Timestamp,
      // Default to 'current' if the field doesn't exist in Firestore
      weekType: data['weekType'] ?? 'current', // <<< NEW MAPPING
    );
  }
}