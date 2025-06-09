import 'package:cloud_firestore/cloud_firestore.dart';

class Brochure {
  final String id;
  final String marketName;
  final String title;
  final String validity;
  // CHANGED: Field name updated to match Firestore
  final String thumbnail; 
  // CHANGED: Field name updated to match Firestore
  final List<String> pages; 
  final Timestamp timestamp;

  Brochure({
    required this.id,
    required this.marketName,
    required this.title,
    required this.validity,
    // CHANGED: Parameter name updated
    required this.thumbnail, 
    // CHANGED: Parameter name updated
    required this.pages, 
    required this.timestamp,
  });

  // Firestore DocumentSnapshot'tan Brochure nesnesi oluşturmak için factory constructor
  factory Brochure.fromFirestore(DocumentSnapshot doc) {
    Map<String, dynamic> data = doc.data() as Map<String, dynamic>;
    return Brochure(
      id: doc.id,
      marketName: data['marketName'] ?? 'Bilinmeyen Market',
      title: data['title'] ?? 'Bilinmeyen Başlık',
      validity: data['validity'] ?? 'Geçerlilik Yok',
      // CHANGED: Mapping from 'thumbnail' field in Firestore
      thumbnail: data['thumbnail'] ?? '', 
      // CHANGED: Mapping from 'pages' field in Firestore
      pages: List<String>.from(data['pages'] ?? []), 
      timestamp: data['timestamp'] as Timestamp,
    );
  }
}
