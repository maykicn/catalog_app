import 'package:flutter/material.dart';
import 'package:catalog_app/brochure_list_screen.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:catalog_app/firebase_options.dart';
// 1. Import the dotenv package
import 'package:flutter_dotenv/flutter_dotenv.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  
  // 2. Load the environment variables from the .env file
  await dotenv.load(fileName: ".env");

  // 3. Initialize Firebase as before
  await Firebase.initializeApp(
    options: DefaultFirebaseOptions.currentPlatform,
  );
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Profital Clone MVP',
      theme: ThemeData(
        primarySwatch: Colors.blue,
        appBarTheme: const AppBarTheme(
          backgroundColor: Colors.red, // Consistent AppBar color
          foregroundColor: Colors.white,
        ),
      ),
      home: const BrochureListScreen(),
      debugShowCheckedModeBanner: false,
    );
  }
}
