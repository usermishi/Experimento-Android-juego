package com.example.usermishi

import android.animation.Animator
import android.animation.AnimatorListenerAdapter
import android.animation.ObjectAnimator
import android.animation.ValueAnimator
import android.graphics.Color
import android.graphics.Rect
import android.graphics.drawable.ShapeDrawable
import android.graphics.drawable.shapes.OvalShape
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.util.Log
import android.view.Gravity
import android.view.MotionEvent
import android.view.View
import android.view.ViewTreeObserver
import android.view.animation.AccelerateDecelerateInterpolator
import android.view.animation.LinearInterpolator
import android.widget.Button
import android.widget.FrameLayout
import android.widget.ImageView
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import androidx.constraintlayout.widget.ConstraintLayout

class MainActivity : AppCompatActivity(), View.OnTouchListener {

    private lateinit var catView: ImageView
    private lateinit var rootLayout: ConstraintLayout
    private lateinit var stickContainer: FrameLayout 
    private lateinit var platformView: View 
    private lateinit var berryView: View    

    private lateinit var gameOverTextView: TextView
    private lateinit var restartButton: Button
    private lateinit var scoreTextView: TextView 

    private var isJumping = false
    private var isCatOnStick = false
    private var catGroundY = 0f 
    private var catRelativeXOnStick = 0f 
    private var initialCatX = 0f 

    private var score = 0 

    private lateinit var stickAnimator: ObjectAnimator
    private var upAnimator: ObjectAnimator? = null
    private var fallAnimator: ObjectAnimator? = null

    private val gameLoopHandler = Handler(Looper.getMainLooper())
    private lateinit var gameLoopRunnable: Runnable
    private var isGameOver = false


    companion object {
        private const val TAG = "MainActivity"

        // Cat properties
        private const val JUMP_HEIGHT = 300f
        private const val JUMP_DURATION = 400L 
        private const val FALL_DURATION_FROM_PEAK = 400L 
        private const val FALL_DURATION_GENERAL = 600L 

        // Stick properties
        private const val STICK_WIDTH = 200f
        private const val STICK_HEIGHT = 50f
        private val STICK_COLOR = Color.GREEN
        private const val STICK_ANIMATION_DURATION = 3000L
        private const val STICK_VERTICAL_OFFSET = 150f

        // Berry properties
        private const val BERRY_SIZE = 30f 
        private val BERRY_COLOR = Color.RED
        private const val BERRY_SCORE = 10 

        private const val GAME_LOOP_DELAY = 16L 
        private const val LANDING_TOLERANCE = 25f 
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        catView = findViewById(R.id.cat_view)
        rootLayout = findViewById(R.id.root_layout)
        gameOverTextView = findViewById(R.id.game_over_text)
        restartButton = findViewById(R.id.restart_button)
        scoreTextView = findViewById(R.id.score_text_view) 
        
        rootLayout.setOnTouchListener(this)

        restartButton.setOnClickListener {
            restartGame()
        }

        catView.viewTreeObserver.addOnGlobalLayoutListener(object : ViewTreeObserver.OnGlobalLayoutListener {
            override fun onGlobalLayout() {
                catView.viewTreeObserver.removeOnGlobalLayoutListener(this)
                initialCatX = catView.x 
            }
        })
        
        updateScoreDisplay() 
        setupStickAndBerry() 
        // setupGameLoop is called after stick animation starts to ensure rootLayout.width is available
    }

    private fun updateScoreDisplay() {
        scoreTextView.text = "Score: $score"
    }

    private fun setupStickAndBerry() {
        stickContainer = FrameLayout(this)
        val containerLayoutParams = ConstraintLayout.LayoutParams(STICK_WIDTH.toInt(), STICK_HEIGHT.toInt())
        stickContainer.layoutParams = containerLayoutParams
        rootLayout.addView(stickContainer)

        platformView = View(this)
        platformView.setBackgroundColor(STICK_COLOR)
        val platformLayoutParams = FrameLayout.LayoutParams(
            FrameLayout.LayoutParams.MATCH_PARENT, 
            FrameLayout.LayoutParams.MATCH_PARENT 
        )
        stickContainer.addView(platformView)

        berryView = View(this)
        val berryDrawable = ShapeDrawable(OvalShape())
        berryDrawable.paint.color = BERRY_COLOR
        berryView.background = berryDrawable
        
        val berryLayoutParams = FrameLayout.LayoutParams(BERRY_SIZE.toInt(), BERRY_SIZE.toInt())
        berryLayoutParams.gravity = Gravity.CENTER_HORIZONTAL 
        berryLayoutParams.topMargin = (STICK_HEIGHT / 2 - BERRY_SIZE).toInt() 
        if (berryLayoutParams.topMargin < 0) berryLayoutParams.topMargin = 0 

        stickContainer.addView(berryView, berryLayoutParams)
        berryView.visibility = View.VISIBLE 

        catView.bringToFront() 

        rootLayout.viewTreeObserver.addOnGlobalLayoutListener(object : ViewTreeObserver.OnGlobalLayoutListener {
            override fun onGlobalLayout() {
                if (rootLayout.width == 0) return 

                rootLayout.viewTreeObserver.removeOnGlobalLayoutListener(this)
                stickContainer.x = rootLayout.width.toFloat() 
                stickContainer.y = rootLayout.height.toFloat() - STICK_HEIGHT - STICK_VERTICAL_OFFSET
                animateStickContainer() 
                setupGameLoop() // Start game loop after stick is positioned and animation is ready
            }
        })
    }

    private fun animateStickContainer() {
        stickContainer.translationX = 0f 

        stickAnimator = ObjectAnimator.ofFloat(stickContainer, "translationX", 0f, -(rootLayout.width.toFloat() + STICK_WIDTH))
        stickAnimator.duration = STICK_ANIMATION_DURATION
        stickAnimator.interpolator = LinearInterpolator()
        stickAnimator.repeatCount = ValueAnimator.INFINITE
        stickAnimator.repeatMode = ValueAnimator.RESTART
        
        stickAnimator.addListener(object: AnimatorListenerAdapter() {
            override fun onAnimationRepeat(animation: Animator) {
                if (!isGameOver) { 
                    berryView.visibility = View.VISIBLE
                    Log.d(TAG, "Stick animation repeated, berry reset to VISIBLE.")
                }
            }
        })
        stickAnimator.start()
    }

    private fun setupGameLoop() {
        // Ensure previous callbacks are removed before posting a new one, especially if called multiple times.
        gameLoopHandler.removeCallbacksAndMessages(null)
        gameLoopRunnable = Runnable {
            if (isGameOver || !this::stickContainer.isInitialized || !stickContainer.isAttachedToWindow || !catView.isAttachedToWindow) {
                if (!isGameOver) gameLoopHandler.postDelayed(gameLoopRunnable, GAME_LOOP_DELAY) 
                return@Runnable
            }
            checkStickCollision() 
            updateCatPositionOnStick()
            checkBerryCollision() 
            checkGameOverCondition() 
            gameLoopHandler.postDelayed(gameLoopRunnable, GAME_LOOP_DELAY)
        }
        gameLoopHandler.postDelayed(gameLoopRunnable, GAME_LOOP_DELAY)
        Log.d(TAG, "Game loop started/restarted.");
    }

    private fun getScreenBoundingBox(view: View): Rect {
        val outRect = Rect()
        val location = IntArray(2)
        view.getLocationOnScreen(location) 
        outRect.left = location[0]
        outRect.top = location[1]
        outRect.right = outRect.left + view.width
        outRect.bottom = outRect.top + view.height
        return outRect
    }

    private fun checkStickCollision() {
        val catRect = getScreenBoundingBox(catView) 
        val platformRect = getScreenBoundingBox(platformView) 

        if (Rect.intersects(catRect, platformRect)) { 
            val catBottom = catRect.bottom
            val platformTop = platformRect.top
            
            if ((isJumping || fallAnimator?.isRunning == true) && 
                catBottom >= platformTop && catBottom <= platformTop + LANDING_TOLERANCE && 
                !isCatOnStick) {
                
                Log.d(TAG, "StickCollision: Cat landed on stick. Cat bottom: $catBottom, Platform top: $platformTop")
                isCatOnStick = true
                isJumping = false
                fallAnimator?.cancel() 
                upAnimator?.cancel()   

                val requiredTranslationY = catView.translationY + (platformTop - catRect.bottom) 
                catView.translationY = requiredTranslationY
                
                catRelativeXOnStick = catRect.left.toFloat() - getScreenBoundingBox(stickContainer).left.toFloat()
            }
        } else { 
            if (isCatOnStick) { 
                Log.d(TAG, "StickCollision: Cat no longer on stick.")
                isCatOnStick = false
                if (!isJumping) { 
                    performFall(FALL_DURATION_GENERAL, catView.translationY) 
                }
            }
        }
    }
    
    private fun checkBerryCollision() {
        if (berryView.visibility != View.VISIBLE) return

        val catRect = getScreenBoundingBox(catView)
        val berryRect = getScreenBoundingBox(berryView)

        if (Rect.intersects(catRect, berryRect)) {
            Log.d(TAG, "Berry collected!")
            score += BERRY_SCORE 
            updateScoreDisplay() 
            berryView.visibility = View.GONE
        }
    }

    private fun updateCatPositionOnStick() {
        if (isCatOnStick) {
            val stickContainerScreenX = getScreenBoundingBox(stickContainer).left.toFloat()
            val rootLayoutScreenX = getScreenBoundingBox(rootLayout).left.toFloat() 
            catView.x = stickContainerScreenX + catRelativeXOnStick - rootLayoutScreenX
            
            val platformTop = getScreenBoundingBox(platformView).top
            val catScreenBottom = getScreenBoundingBox(catView).bottom
            if (Math.abs(catScreenBottom - platformTop) > 1) { 
                 val requiredTranslationY = catView.translationY + (platformTop - catScreenBottom)
                 catView.translationY = requiredTranslationY
            }
        }
    }

    private fun performFall(duration: Long, startYTranslation: Float) {
        if (isGameOver) return
        if (fallAnimator?.isRunning == true && fallAnimator?.values?.get(0)?.animatedValue == catGroundY) {
             return
        }
        isJumping = false 
        isCatOnStick = false 

        fallAnimator?.cancel() 

        Log.d(TAG, "PerformFall: Starting fall from TranslationY $startYTranslation to $catGroundY")
        fallAnimator = ObjectAnimator.ofFloat(catView, "translationY", startYTranslation, catGroundY).apply {
            this.duration = duration 
            interpolator = LinearInterpolator() 
            addListener(object : AnimatorListenerAdapter() {
                override fun onAnimationEnd(animation: Animator) {
                    Log.d(TAG, "PerformFall: Fall animation ended. Cat at translationY: ${catView.translationY}")
                }
            })
        }
        fallAnimator?.start()
    }

    override fun onTouch(v: View?, event: MotionEvent?): Boolean {
        if (isGameOver) return false 

        if (event?.action == MotionEvent.ACTION_DOWN) {
            if (!isJumping && !isCatOnStick) { 
                performJump(catGroundY)
            } else if (isCatOnStick && !isJumping) { 
                performJump(catView.translationY) 
            }
            return true 
        }
        return false 
    }

    private fun performJump(startYTranslation: Float) {
        if (isJumping || isGameOver) return 

        Log.d(TAG, "PerformJump: Starting jump from TranslationY: $startYTranslation")
        isJumping = true
        isCatOnStick = false 
        
        fallAnimator?.cancel() 
        upAnimator?.cancel()

        upAnimator = ObjectAnimator.ofFloat(catView, "translationY", startYTranslation, startYTranslation - JUMP_HEIGHT).apply {
            duration = JUMP_DURATION / 2
            interpolator = AccelerateDecelerateInterpolator()
            addListener(object : AnimatorListenerAdapter() {
                override fun onAnimationEnd(animation: Animator) {
                    if (isJumping) { 
                        performFallFromPeak(startYTranslation - JUMP_HEIGHT)
                    }
                }
            })
        }
        upAnimator?.start()
    }

    private fun performFallFromPeak(peakYTranslation: Float) {
        if (isGameOver) return
        Log.d(TAG, "PerformFallFromPeak: Starting fall from peak TranslationY: $peakYTranslation towards $catGroundY")
        fallAnimator = ObjectAnimator.ofFloat(catView, "translationY", peakYTranslation, catGroundY).apply {
            duration = FALL_DURATION_FROM_PEAK
            interpolator = AccelerateDecelerateInterpolator() 
            addListener(object : AnimatorListenerAdapter() {
                override fun onAnimationEnd(animation: Animator) {
                    Log.d(TAG, "PerformFallFromPeak: Fall from peak ended. Cat at translationY: ${catView.translationY}")
                    isJumping = false
                }
            })
        }
        fallAnimator?.start()
    }

    private fun checkGameOverCondition() {
        if (isGameOver) return

        if (!isJumping && !isCatOnStick && catView.translationY >= catGroundY - 1f) { 
            if (this::stickAnimator.isInitialized && stickAnimator.isRunning) {
                 Log.e(TAG, "Game Over - Cat hit the ground! TranslationY: ${catView.translationY}, GroundY: $catGroundY. Score: $score")
                 gameOver()
            }
        }
        
        if (rootLayout.height > 0) { 
            val catRect = getScreenBoundingBox(catView) 
            if (catRect.top > rootLayout.height) { 
                Log.e(TAG, "Game Over - Cat fell below screen! Cat top: ${catRect.top}, Screen height: ${rootLayout.height}. Score: $score")
                gameOver()
            }
        }
    }
    
    private fun gameOver() {
        if (isGameOver) return 
        isGameOver = true

        Log.e(TAG, "GAME OVER sequence initiated! Final Score: $score")
        if (this::stickAnimator.isInitialized) stickAnimator.cancel()
        
        gameLoopHandler.removeCallbacksAndMessages(null) 

        upAnimator?.cancel()
        fallAnimator?.cancel()
        
        rootLayout.setOnTouchListener(null) 
        isJumping = false
        isCatOnStick = false

        gameOverTextView.text = "Game Over\nFinal Score: $score" 
        gameOverTextView.visibility = View.VISIBLE
        restartButton.visibility = View.VISIBLE
        gameOverTextView.bringToFront()
        restartButton.bringToFront()
        scoreTextView.bringToFront() 
    }

    private fun restartGame() {
        Log.d(TAG, "Restarting game...")
        isGameOver = false

        gameOverTextView.visibility = View.GONE
        restartButton.visibility = View.GONE

        score = 0 
        updateScoreDisplay() 

        catView.translationY = catGroundY 
        catView.translationX = 0f 
        catView.x = initialCatX 
        isJumping = false
        isCatOnStick = false
        upAnimator?.cancel()
        fallAnimator?.cancel()

        if (this::stickAnimator.isInitialized) stickAnimator.cancel()
        stickContainer.translationX = 0f 
        if (rootLayout.width > 0) { 
            stickContainer.x = rootLayout.width.toFloat() 
        } else {
             rootLayout.viewTreeObserver.addOnGlobalLayoutListener(object : ViewTreeObserver.OnGlobalLayoutListener {
                override fun onGlobalLayout() {
                    if (rootLayout.width == 0) return
                    rootLayout.viewTreeObserver.removeOnGlobalLayoutListener(this)
                    stickContainer.x = rootLayout.width.toFloat()
                }
            })
        }
        berryView.visibility = View.VISIBLE
        animateStickContainer() // This will re-initialize and start stickAnimator

        setupGameLoop() // This re-posts the runnable

        rootLayout.setOnTouchListener(this) 
    }

    override fun onPause() {
        super.onPause()
        if (!isGameOver && this::stickAnimator.isInitialized && stickAnimator.isRunning) { 
            Log.d(TAG, "Game paused.")
            stickAnimator.pause()
            upAnimator?.pause()
            fallAnimator?.pause()
            gameLoopHandler.removeCallbacksAndMessages(null) 
        }
    }

    override fun onResume() {
        super.onResume()
        if (!isGameOver) {
            var wasPaused = false
            if (this::stickAnimator.isInitialized && stickAnimator.isPaused) {
                stickAnimator.resume()
                wasPaused = true // Indicate that animations were paused and are now resumed
            }
            if (this::upAnimator.isInitialized && upAnimator?.isPaused == true) {
                 upAnimator?.resume()
                 wasPaused = true
            }
            if (this::fallAnimator.isInitialized && fallAnimator?.isPaused == true) {
                fallAnimator?.resume()
                wasPaused = true
            }

            // Ensure game loop is running if game is not over.
            // This covers resuming from pause, and also initial start if not already covered.
            gameLoopHandler.removeCallbacksAndMessages(null) // Clear any old ones
            gameLoopHandler.postDelayed(gameLoopRunnable, GAME_LOOP_DELAY)
            if(wasPaused) Log.d(TAG, "Game resumed, animations and loop restarted.")
            else Log.d(TAG, "Game loop (re)started in onResume (game not over).")

        }
    }

    override fun onDestroy() {
        super.onDestroy()
        isGameOver = true; 
        gameLoopHandler.removeCallbacksAndMessages(null)
        if (this::stickAnimator.isInitialized) stickAnimator.cancel()
        upAnimator?.cancel()
        fallAnimator?.cancel()
    }
}
