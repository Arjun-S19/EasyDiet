import unittest
from gemini_demo import validate_recipe_output

class RecipeOutputValidationTests(unittest.TestCase):
    '''Unit tests for the validate_recipe_output function in gemini_demo.py'''
   
    def test_validate_recipe_output_accepts_valid_text(self) -> None:
        '''Test that valid recipe text is correctly parsed'''
        valid_text = (
            "Garden Omelette\n"
            "Servings: 2\n"
            "Time: 20 minutes\n"
            "\n"
            "Ingredients:\n"
            "- 4 eggs\n"
            "- 1 bell pepper\n"
            "- 2 cloves garlic\n"
            "\n"
            "Instructions:\n"
            "1. Beat the eggs with salt.\n"
            "2. Cook the mixture gently until set.\n"
            "\n"
            "Herbed Roast Chicken\n"
            "Servings: 4\n"
            "Time: 60 minutes\n"
            "\n"
            "Ingredients:\n"
            "- 1 whole chicken\n"
            "- 1 tbsp olive oil\n"
            "- 1 tsp salt\n"
            "\n"
            "Instructions:\n"
            "1. Season the chicken thoroughly.\n"
            "2. Roast until the juices run clear.\n"
        )

        parsed = validate_recipe_output(valid_text)
        self.assertEqual(len(parsed), 2)
        self.assertEqual(parsed[0]["title"], "Garden Omelette")
        self.assertEqual(parsed[0]["servings"], 2)
        self.assertEqual(parsed[0]["instructions"][0], "Beat the eggs with salt.")

    def test_validate_recipe_output_requires_ingredient_section(self) -> None:
        '''Test that missing ingredient section raises ValueError'''
        missing_ingredients = (
            "Simple Scramble\n"
            "Servings: 2\n"
            "Time: 10 minutes\n"
            "\n"
            "Instructions:\n"
            "1. Cook everything together.\n"
            "\n"
            "Quick Roast\n"
            "Servings: 3\n"
            "Time: 45 minutes\n"
            "\n"
            "Ingredients:\n"
            "- whole chicken\n"
            "\n"
            "Instructions:\n"
            "1. Roast thoroughly.\n"
        )

        with self.assertRaises(ValueError):
            validate_recipe_output(missing_ingredients)

    def test_validate_recipe_output_requires_numbered_instructions(self) -> None:
        '''Test that unnumbered instructions raise ValueError'''
        unnumbered_instructions = (
            "Weeknight Pasta\n"
            "Servings: 2\n"
            "Time: 25 minutes\n"
            "\n"
            "Ingredients:\n"
            "- penne pasta\n"
            "- olive oil\n"
            "\n"
            "Instructions:\n"
            "Boil the pasta.\n"
            "\n"
            "Quick Salad\n"
            "Servings: 2\n"
            "Time: 10 minutes\n"
            "\n"
            "Ingredients:\n"
            "- bell pepper\n"
            "\n"
            "Instructions:\n"
            "1. Toss together.\n"
        )

        with self.assertRaises(ValueError):
            validate_recipe_output(unnumbered_instructions)


if __name__ == "__main__":
    unittest.main()
